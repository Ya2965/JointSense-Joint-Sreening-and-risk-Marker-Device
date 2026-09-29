#include <Wire.h>
#include <math.h>
#include "7Semi_BMI270.h"

// ============================================================
// DUAL BMI270 - SEATED KNEE EXTENSION TEST  (rectified)
//
// ESP32 DEVKIT V1
//   THIGH BMI270: SDA = GPIO 21, SCL = GPIO 22
//   SHANK BMI270: SDA = GPIO 16, SCL = GPIO 17
//   Both sensors use address 0x69 (separate I2C buses).
//`1  
// REFERENCE
//   Seated starting position = 0 degrees.
//   Knee extension increases the reported angle.
//
// CHANGES vs the original
//   1. Madgwick filters are SEEDED FROM GRAVITY before settling, so they
//      start converged. (Starting from "sensor flat" left the filters still
//      converging when the neutral pose was captured, which showed up as a
//      ~20 deg offset on a perfectly still leg.)
//   2. Calibration loops use the MEASURED dt instead of a fixed 0.01 s.
//   3. Angle uses atan2f (better conditioned than acos near 0).
//   4. Post-calibration self-check: warns if the leg moved during capture.
//   5. Optional machine-readable CSV output for the Python logger
//      (OUTPUT_CSV = 1) and live beta tuning with 'b0.05' over serial.
//
// LIMITS (unchanged - know these when you interpret results)
//   - Angle is an UNSIGNED magnitude of relative rotation from the start
//     pose. Do not flex beyond the start pose.
//   - 6-axis fusion cannot observe yaw, so relative yaw drifts slowly.
//     Keep trials short and recalibrate between subjects.
//   - Gyro scale below assumes +/-2000 dps. VERIFY the 7Semi library's
//     configured range (a 90 deg bench rotation should read ~90).
// ============================================================


// ============================================================
// I2C PINS
// ============================================================

#define THIGH_SDA 21
#define THIGH_SCL 22

#define SHANK_SDA 16
#define SHANK_SCL 17

#define BMI270_ADDRESS 0x69


// ============================================================
// SETTINGS
// ============================================================

#define GYRO_CAL_SAMPLES       500
#define GYRO_CAL_DELAY_MS      10

#define SEED_SAMPLES           50
#define SEED_DELAY_MS          10

#define FILTER_SETTLE_SAMPLES  300
#define FILTER_SETTLE_DELAY_MS 10

#define NEUTRAL_CAL_SAMPLES    300
#define NEUTRAL_CAL_DELAY_MS   10

#define CHECK_SAMPLES          50
#define CHECK_MAX_RESIDUAL_DEG 2.0f

// 0 = human-readable serial lines, 1 = CSV for validate_imu_vs_goniometer.py
#define OUTPUT_CSV 0

const float GYRO_LSB_PER_DPS = 16.4f;     // +/-2000 dps range (verify!)
const float ACC_LSB_PER_G    = 16384.0f;  // +/-2 g (scale is irrelevant: accel is normalized)


// ============================================================
// MADGWICK GAIN (tunable live: send  b0.05  over serial)
// ============================================================

float BETA = 0.08f;


// ============================================================
// I2C BUSES AND IMUS
// ============================================================

TwoWire I2C_Thigh = TwoWire(0);
TwoWire I2C_Shank = TwoWire(1);

BMI270_7Semi imuThigh;
BMI270_7Semi imuShank;


// ============================================================
// STATE
// ============================================================

float thighBiasGX = 0.0f, thighBiasGY = 0.0f, thighBiasGZ = 0.0f;
float shankBiasGX = 0.0f, shankBiasGY = 0.0f, shankBiasGZ = 0.0f;

float tq0 = 1.0f, tq1 = 0.0f, tq2 = 0.0f, tq3 = 0.0f;   // thigh orientation
float sq0 = 1.0f, sq1 = 0.0f, sq2 = 0.0f, sq3 = 0.0f;   // shank orientation

// Relative quaternion at the seated starting pose (= 0 degrees).
// The actual on-body sensor relationship is measured, not assumed 90 deg.
float neutralRQ0 = 1.0f, neutralRQ1 = 0.0f, neutralRQ2 = 0.0f, neutralRQ3 = 0.0f;

unsigned long lastTime = 0;
unsigned long experimentStartTime = 0;


// ============================================================
// SENSOR READ
// ============================================================

bool readBothSensors(bmi2_sens_data &thighData, bmi2_sens_data &shankData)
{
  memset(&thighData, 0, sizeof(thighData));
  memset(&shankData, 0, sizeof(shankData));

  int8_t thighStatus = imuThigh.readSample(thighData);
  int8_t shankStatus = imuShank.readSample(shankData);

  return (thighStatus == 0 && shankStatus == 0);
}


// ============================================================
// QUATERNION MATH
// ============================================================

void normalizeQuaternion(float &q0, float &q1, float &q2, float &q3)
{
  float norm = sqrtf(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);

  if (norm <= 0.0f)
  {
    q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
    return;
  }

  q0 /= norm; q1 /= norm; q2 /= norm; q3 /= norm;
}

void quaternionConjugate(float q0, float q1, float q2, float q3,
                         float &r0, float &r1, float &r2, float &r3)
{
  r0 = q0; r1 = -q1; r2 = -q2; r3 = -q3;
}

// RESULT = A x B
void quaternionMultiply(float a0, float a1, float a2, float a3,
                        float b0, float b1, float b2, float b3,
                        float &r0, float &r1, float &r2, float &r3)
{
  r0 = a0 * b0 - a1 * b1 - a2 * b2 - a3 * b3;
  r1 = a0 * b1 + a1 * b0 + a2 * b3 - a3 * b2;
  r2 = a0 * b2 - a1 * b3 + a2 * b0 + a3 * b1;
  r3 = a0 * b3 + a1 * b2 - a2 * b1 + a3 * b0;
}

// Total rotation angle of a unit quaternion, folded to 0..180 deg.
float quaternionAngleDeg(float q0, float q1, float q2, float q3)
{
  float v = sqrtf(q1 * q1 + q2 * q2 + q3 * q3);
  float a = 2.0f * atan2f(v, q0) * RAD_TO_DEG;

  if (a > 180.0f) a = 360.0f - a;

  return a;
}


// ============================================================
// MADGWICK 6-AXIS UPDATE
// gx gy gz = rad/sec, ax ay az = any units (normalized), dt = seconds
// ============================================================

void MadgwickUpdate(float &q0, float &q1, float &q2, float &q3,
                    float gx, float gy, float gz,
                    float ax, float ay, float az,
                    float dt)
{
  float norm = sqrtf(ax * ax + ay * ay + az * az);

  if (norm <= 0.0f) return;

  ax /= norm; ay /= norm; az /= norm;

  float _2q0 = 2.0f * q0;
  float _2q1 = 2.0f * q1;
  float _2q2 = 2.0f * q2;
  float _2q3 = 2.0f * q3;

  float _4q0 = 4.0f * q0;
  float _4q1 = 4.0f * q1;
  float _4q2 = 4.0f * q2;

  float _8q1 = 8.0f * q1;
  float _8q2 = 8.0f * q2;

  float q0q0 = q0 * q0;
  float q1q1 = q1 * q1;
  float q2q2 = q2 * q2;
  float q3q3 = q3 * q3;

  // Gradient descent step
  float s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;

  float s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay
           - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;

  float s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay
           - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;

  float s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;

  norm = sqrtf(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);

  if (norm > 0.0f)
  {
    s0 /= norm; s1 /= norm; s2 /= norm; s3 /= norm;
  }

  // Quaternion derivative
  float qDot0 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz) - BETA * s0;
  float qDot1 = 0.5f * ( q0 * gx + q2 * gz - q3 * gy) - BETA * s1;
  float qDot2 = 0.5f * ( q0 * gy - q1 * gz + q3 * gx) - BETA * s2;
  float qDot3 = 0.5f * ( q0 * gz + q1 * gy - q2 * gx) - BETA * s3;

  q0 += qDot0 * dt;
  q1 += qDot1 * dt;
  q2 += qDot2 * dt;
  q3 += qDot3 * dt;

  normalizeQuaternion(q0, q1, q2, q3);
}


// ============================================================
// SEED A QUATERNION FROM GRAVITY (roll/pitch from accelerometer, yaw = 0)
//
// With this the filter starts with zero gravity error instead of having to
// converge from "sensor lying flat", which at BETA = 0.08 takes far longer
// than the calibration window.
// ============================================================

void initQuaternionFromAccel(float ax, float ay, float az,
                             float &q0, float &q1, float &q2, float &q3)
{
  float n = sqrtf(ax * ax + ay * ay + az * az);

  if (n <= 0.0f) return;

  ax /= n; ay /= n; az /= n;

  float roll  = atan2f(ay, az);
  float pitch = atan2f(-ax, sqrtf(ay * ay + az * az));

  float cr = cosf(roll * 0.5f),  sr = sinf(roll * 0.5f);
  float cp = cosf(pitch * 0.5f), sp = sinf(pitch * 0.5f);

  q0 =  cr * cp;
  q1 =  sr * cp;
  q2 =  cr * sp;
  q3 = -sr * sp;
}


// ============================================================
// MEASURED TIME STEP FOR CALIBRATION LOOPS
// ============================================================

float stepDt()
{
  static unsigned long prev = 0;

  unsigned long now = micros();
  float dt = (prev == 0) ? 0.01f : (now - prev) / 1000000.0f;
  prev = now;

  if (dt <= 0.0f || dt > 0.1f) dt = 0.01f;

  return dt;
}


// ============================================================
// RELATIVE ORIENTATION
// ============================================================

// Qrel = inverse(Qthigh) x Qshank
void getRelativeQuaternion(float &rq0, float &rq1, float &rq2, float &rq3)
{
  float i0, i1, i2, i3;

  quaternionConjugate(tq0, tq1, tq2, tq3, i0, i1, i2, i3);
  quaternionMultiply(i0, i1, i2, i3, sq0, sq1, sq2, sq3, rq0, rq1, rq2, rq3);
  normalizeQuaternion(rq0, rq1, rq2, rq3);
}

// Qcorrected = inverse(Qneutral) x Qcurrent   (start pose -> 0 degrees)
void removeNeutralOffset(float rq0, float rq1, float rq2, float rq3,
                         float &o0, float &o1, float &o2, float &o3)
{
  float n0, n1, n2, n3;

  quaternionConjugate(neutralRQ0, neutralRQ1, neutralRQ2, neutralRQ3,
                      n0, n1, n2, n3);
  quaternionMultiply(n0, n1, n2, n3, rq0, rq1, rq2, rq3, o0, o1, o2, o3);
  normalizeQuaternion(o0, o1, o2, o3);
}


// ============================================================
// UPDATE BOTH FILTERS FROM ONE SAMPLE PAIR
// ============================================================

bool updateFilters(float dt)
{
  bmi2_sens_data thighData;
  bmi2_sens_data shankData;

  if (!readBothSensors(thighData, shankData)) return false;

  float tax = thighData.acc.x / ACC_LSB_PER_G;
  float tay = thighData.acc.y / ACC_LSB_PER_G;
  float taz = thighData.acc.z / ACC_LSB_PER_G;

  float sax = shankData.acc.x / ACC_LSB_PER_G;
  float say = shankData.acc.y / ACC_LSB_PER_G;
  float saz = shankData.acc.z / ACC_LSB_PER_G;

  // RAW -> dps -> rad/sec
  float tgx = (((float)thighData.gyr.x - thighBiasGX) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;
  float tgy = (((float)thighData.gyr.y - thighBiasGY) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;
  float tgz = (((float)thighData.gyr.z - thighBiasGZ) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;

  float sgx = (((float)shankData.gyr.x - shankBiasGX) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;
  float sgy = (((float)shankData.gyr.y - shankBiasGY) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;
  float sgz = (((float)shankData.gyr.z - shankBiasGZ) / GYRO_LSB_PER_DPS) * DEG_TO_RAD;

  MadgwickUpdate(tq0, tq1, tq2, tq3, tgx, tgy, tgz, tax, tay, taz, dt);
  MadgwickUpdate(sq0, sq1, sq2, sq3, sgx, sgy, sgz, sax, say, saz, dt);

  return true;
}


// ============================================================
// STEP 1: GYRO BIAS CALIBRATION
// ============================================================

void calibrateGyros()
{
  Serial.println();
  Serial.println("==========================================");
  Serial.println("STEP 1: GYRO BIAS CALIBRATION");
  Serial.println("==========================================");
  Serial.println();
  Serial.println("SEATED POSITION:");
  Serial.println("Sit comfortably.");
  Serial.println("Keep thigh and shank completely still.");
  Serial.println("Do not move the knee.");
  Serial.println();
  Serial.println("Calibration starts in 5 seconds...");

  delay(5000);

  long long tSumX = 0, tSumY = 0, tSumZ = 0;
  long long sSumX = 0, sSumY = 0, sSumZ = 0;
  int validSamples = 0;

  Serial.println();
  Serial.println("CALIBRATING...");
  Serial.println("DO NOT MOVE.");

  for (int i = 0; i < GYRO_CAL_SAMPLES; i++)
  {
    bmi2_sens_data thighData;
    bmi2_sens_data shankData;

    if (readBothSensors(thighData, shankData))
    {
      tSumX += thighData.gyr.x;
      tSumY += thighData.gyr.y;
      tSumZ += thighData.gyr.z;

      sSumX += shankData.gyr.x;
      sSumY += shankData.gyr.y;
      sSumZ += shankData.gyr.z;

      validSamples++;
    }

    if (i % 50 == 0) Serial.print(".");

    delay(GYRO_CAL_DELAY_MS);
  }

  Serial.println();

  if (validSamples == 0)
  {
    Serial.println("GYRO CALIBRATION FAILED.");
    while (true) delay(100);
  }

  thighBiasGX = (float)tSumX / validSamples;
  thighBiasGY = (float)tSumY / validSamples;
  thighBiasGZ = (float)tSumZ / validSamples;

  shankBiasGX = (float)sSumX / validSamples;
  shankBiasGY = (float)sSumY / validSamples;
  shankBiasGZ = (float)sSumZ / validSamples;

  Serial.println();
  Serial.println("GYRO BIAS CALIBRATION COMPLETE.");
}


// ============================================================
// STEP 2: SEED FILTERS FROM GRAVITY (leg still)
// ============================================================

void seedFiltersFromAccel()
{
  Serial.println();
  Serial.println("==========================================");
  Serial.println("STEP 2: FILTER INITIALIZATION (GRAVITY)");
  Serial.println("==========================================");
  Serial.println("Remain completely still.");

  float tx = 0.0f, ty = 0.0f, tz = 0.0f;
  float sx = 0.0f, sy = 0.0f, sz = 0.0f;
  int n = 0;

  for (int i = 0; i < SEED_SAMPLES; i++)
  {
    bmi2_sens_data t;
    bmi2_sens_data s;

    if (readBothSensors(t, s))
    {
      tx += t.acc.x; ty += t.acc.y; tz += t.acc.z;
      sx += s.acc.x; sy += s.acc.y; sz += s.acc.z;
      n++;
    }

    delay(SEED_DELAY_MS);
  }

  if (n == 0)
  {
    Serial.println("SEEDING FAILED - continuing from identity (expect an offset).");
    return;
  }

  initQuaternionFromAccel(tx, ty, tz, tq0, tq1, tq2, tq3);
  initQuaternionFromAccel(sx, sy, sz, sq0, sq1, sq2, sq3);

  Serial.println("FILTERS SEEDED.");
}


// ============================================================
// STEP 3: FILTER SETTLING
// ============================================================

void settleFilters()
{
  Serial.println();
  Serial.println("==========================================");
  Serial.println("STEP 3: MADGWICK FILTER SETTLING");
  Serial.println("==========================================");
  Serial.println("Remain completely still.");
  Serial.println("Keep the seated knee position unchanged.");
  Serial.println();

  for (int i = 0; i < FILTER_SETTLE_SAMPLES; i++)
  {
    updateFilters(stepDt());

    if (i % 50 == 0) Serial.print(".");

    delay(FILTER_SETTLE_DELAY_MS);
  }

  Serial.println();
  Serial.println("FILTER SETTLING COMPLETE.");
}


// ============================================================
// STEP 4: SEATED STARTING POSITION -> 0 DEGREES
//
// Whatever relative orientation exists between the thigh and shank sensors
// in this pose becomes 0 degrees. This compensates for sensor mounting
// orientation and the subject's actual starting posture.
// ============================================================

void calibrateSeatedPosition()
{
  Serial.println();
  Serial.println("==========================================");
  Serial.println("STEP 4: SEATED STARTING POSITION");
  Serial.println("CALIBRATION");
  Serial.println("==========================================");
  Serial.println();
  Serial.println("ACTION:");
  Serial.println("Sit on a stable chair, thigh supported and still.");
  Serial.println("Place the knee in the desired starting flexed position.");
  Serial.println("Keep the shank completely still. Do not move.");
  Serial.println();
  Serial.println("THIS POSITION WILL BECOME 0 DEGREES OF KNEE EXTENSION.");
  Serial.println("(Measure the goniometer start angle G0 during the hold.)");
  Serial.println();
  Serial.println("Starting in 5 seconds...");

  delay(5000);

  // Average the relative quaternion over the starting-position samples.
  float sumQ0 = 0.0f, sumQ1 = 0.0f, sumQ2 = 0.0f, sumQ3 = 0.0f;
  float p0 = 1.0f, p1 = 0.0f, p2 = 0.0f, p3 = 0.0f;   // previous sample (sign reference)
  int validSamples = 0;

  Serial.println();
  Serial.println("CAPTURING SEATED REFERENCE...");

  for (int i = 0; i < NEUTRAL_CAL_SAMPLES; i++)
  {
    if (updateFilters(stepDt()))
    {
      float rq0, rq1, rq2, rq3;

      getRelativeQuaternion(rq0, rq1, rq2, rq3);

      // q and -q are the same orientation: keep signs consistent so
      // averaging does not cancel.
      if (validSamples > 0 &&
          rq0 * p0 + rq1 * p1 + rq2 * p2 + rq3 * p3 < 0.0f)
      {
        rq0 = -rq0; rq1 = -rq1; rq2 = -rq2; rq3 = -rq3;
      }

      sumQ0 += rq0; sumQ1 += rq1; sumQ2 += rq2; sumQ3 += rq3;

      p0 = rq0; p1 = rq1; p2 = rq2; p3 = rq3;

      validSamples++;
    }

    if (i % 50 == 0) Serial.print(".");

    delay(NEUTRAL_CAL_DELAY_MS);
  }

  Serial.println();

  if (validSamples == 0)
  {
    Serial.println("SEATED REFERENCE CALIBRATION FAILED.");
    while (true) delay(100);
  }

  neutralRQ0 = sumQ0 / validSamples;
  neutralRQ1 = sumQ1 / validSamples;
  neutralRQ2 = sumQ2 / validSamples;
  neutralRQ3 = sumQ3 / validSamples;

  normalizeQuaternion(neutralRQ0, neutralRQ1, neutralRQ2, neutralRQ3);

  Serial.println();
  Serial.println("SEATED STARTING POSITION SET TO 0 DEGREES.");
}


// ============================================================
// STEP 5: POST-CALIBRATION SELF-CHECK
//
// Leg is still, so the angle should already read ~0. A large residual
// means the leg moved during capture (or a scaling/config problem).
// ============================================================

void verifyCalibration()
{
  float sum = 0.0f;
  int n = 0;

  for (int i = 0; i < CHECK_SAMPLES; i++)
  {
    if (updateFilters(stepDt()))
    {
      float rq0, rq1, rq2, rq3, c0, c1, c2, c3;

      getRelativeQuaternion(rq0, rq1, rq2, rq3);
      removeNeutralOffset(rq0, rq1, rq2, rq3, c0, c1, c2, c3);

      sum += quaternionAngleDeg(c0, c1, c2, c3);
      n++;
    }

    delay(NEUTRAL_CAL_DELAY_MS);
  }

  float residual = (n > 0) ? sum / n : 999.0f;

  Serial.println();
  Serial.print("CALIBRATION CHECK: residual angle = ");
  Serial.print(residual, 2);
  Serial.println(" deg (expect < 1.0)");

  if (residual > CHECK_MAX_RESIDUAL_DEG)
  {
    Serial.println("WARNING: residual is high. The leg probably moved during");
    Serial.println("calibration. Press RESET and repeat, staying completely still.");
  }

  Serial.println();
  Serial.println("==========================================");
  Serial.println("SEATED KNEE EXTENSION TEST READY");
  Serial.println("==========================================");
  Serial.println();
  Serial.println("TEST SEQUENCE:");
  Serial.println("1. HOLD STARTING FLEXED POSITION - 3 SEC");
  Serial.println("2. SLOWLY EXTEND THE KNEE");
  Serial.println("3. HOLD AT PARTIAL EXTENSION");
  Serial.println("4. CONTINUE EXTENDING");
  Serial.println("5. APPROACH FULL EXTENSION");
  Serial.println("6. HOLD - 3 SEC");
  Serial.println("7. SLOWLY RETURN TO STARTING POSITION");
  Serial.println("(Do not flex beyond the starting position.)");
  Serial.println();
  Serial.println("OUTPUT STARTING...");
  Serial.println();
}


// ============================================================
// SERIAL COMMANDS:  b0.05  -> set Madgwick BETA live
// ============================================================

void handleSerialCommands()
{
  if (Serial.available() && Serial.read() == 'b')
  {
    float v = Serial.parseFloat();

    if (v > 0.0f && v <= 2.0f)
    {
      BETA = v;
      Serial.print("BETA=");
      Serial.println(BETA, 3);
    }
  }
}

// ============================================================
// GYRO STILL CHECK - call after calibration, leg held still.
// Prints the mean and noise of the bias-corrected gyro (dps) per axis.
// Mean should be ~0. A mean of 0.05 dps already means ~3 deg/min of drift.
// ============================================================
void gyroStillCheck(int seconds)
{
  const float MAX_MEAN_DPS = 0.05f;
  const int   N = seconds * 50;

  double sumT[3] = {0, 0, 0}, sumS[3] = {0, 0, 0};
  double sqT[3]  = {0, 0, 0}, sqS[3]  = {0, 0, 0};
  int n = 0;

  Serial.println();
  Serial.println("GYRO STILL CHECK - keep the leg completely still...");

  for (int i = 0; i < N; i++)
  {
    bmi2_sens_data t, s;

    if (readBothSensors(t, s))
    {
      float tv[3] = { ((float)t.gyr.x - thighBiasGX) / GYRO_LSB_PER_DPS,
                      ((float)t.gyr.y - thighBiasGY) / GYRO_LSB_PER_DPS,
                      ((float)t.gyr.z - thighBiasGZ) / GYRO_LSB_PER_DPS };
      float sv[3] = { ((float)s.gyr.x - shankBiasGX) / GYRO_LSB_PER_DPS,
                      ((float)s.gyr.y - shankBiasGY) / GYRO_LSB_PER_DPS,
                      ((float)s.gyr.z - shankBiasGZ) / GYRO_LSB_PER_DPS };

      for (int k = 0; k < 3; k++)
      {
        sumT[k] += tv[k]; sqT[k] += tv[k] * tv[k];
        sumS[k] += sv[k]; sqS[k] += sv[k] * sv[k];
      }
      n++;
    }

    delay(20);
  }

  if (n == 0) { Serial.println("GYRO CHECK FAILED: no samples."); return; }

  const char *axis[3] = {"X", "Y", "Z"};
  bool bad = false;

  Serial.println("Bias-corrected gyro while still (dps):");
  Serial.println("        mean     std");

  for (int pass = 0; pass < 2; pass++)
  {
    double *sum = pass == 0 ? sumT : sumS;
    double *sq  = pass == 0 ? sqT  : sqS;

    for (int k = 0; k < 3; k++)
    {
      double mean = sum[k] / n;
      double var  = sq[k] / n - mean * mean;
      double sd   = var > 0 ? sqrt(var) : 0.0;

      Serial.print(pass == 0 ? "THIGH " : "SHANK ");
      Serial.print(axis[k]);
      Serial.print(": ");
      Serial.print(mean, 3);
      Serial.print("  ");
      Serial.println(sd, 3);

      if (fabs(mean) > MAX_MEAN_DPS) bad = true;
    }
  }

  Serial.println(bad ? "RESULT: BIAS TOO HIGH - warm up longer / recalibrate (expect drift)."
                     : "RESULT: OK - gyro bias is small, drift should be low.");
}

// ============================================================
// SETUP
// ============================================================

void setup()
{
  Serial.begin(115200);
  Serial.setTimeout(20);

  delay(2000);

  Serial.println();
  Serial.println("==========================================");
  Serial.println("DUAL BMI270");
  Serial.println("SEATED KNEE EXTENSION TEST");
  Serial.println("==========================================");

  I2C_Thigh.begin(THIGH_SDA, THIGH_SCL, 400000);
  I2C_Shank.begin(SHANK_SDA, SHANK_SCL, 400000);

  delay(500);

  BMI270_7Semi::Config thighConfig;
  thighConfig.bus   = BMI270_7Semi::Bus::I2C;
  thighConfig.i2c   = &I2C_Thigh;
  thighConfig.addr  = BMI270_ADDRESS;
  thighConfig.i2cHz = 400000;

  Serial.println();
  Serial.println("INITIALIZING THIGH BMI270...");

  if (!imuThigh.begin(thighConfig))
  {
    Serial.println("ERROR: THIGH BMI270 INIT FAILED.");
    while (true) delay(100);
  }

  BMI270_7Semi::Config shankConfig;
  shankConfig.bus   = BMI270_7Semi::Bus::I2C;
  shankConfig.i2c   = &I2C_Shank;
  shankConfig.addr  = BMI270_ADDRESS;
  shankConfig.i2cHz = 400000;

  Serial.println("INITIALIZING SHANK BMI270...");

  if (!imuShank.begin(shankConfig))
  {
    Serial.println("ERROR: SHANK BMI270 INIT FAILED.");
    while (true) delay(100);
  }

  Serial.println();
  Serial.println("BOTH BMI270 SENSORS READY.");

  calibrateGyros();          // 1. gyro bias
  seedFiltersFromAccel();    // 2. start filters converged
  settleFilters();           // 3. settle
  calibrateSeatedPosition(); // 4. capture 0-degree reference
  verifyCalibration();       // 5. self-check
  gyroStillCheck(5);         // 6. gyro drift check (5 seconds, stay still)

  experimentStartTime = micros();
  lastTime = micros();
}


// ============================================================
// MAIN LOOP
// ============================================================

void loop()
{
  handleSerialCommands();

  unsigned long currentTime = micros();
  float dt = (currentTime - lastTime) / 1000000.0f;
  lastTime = currentTime;

  if (dt <= 0.0f || dt > 0.1f) dt = 0.01f;

  if (!updateFilters(dt))
  {
    Serial.println("SENSOR READ ERROR");
    return;
  }

  float rq0, rq1, rq2, rq3;
  getRelativeQuaternion(rq0, rq1, rq2, rq3);

  float crq0, crq1, crq2, crq3;
  removeNeutralOffset(rq0, rq1, rq2, rq3, crq0, crq1, crq2, crq3);

  // Total relative rotation from the seated start pose (0 deg = start).
  float extensionAngle = quaternionAngleDeg(crq0, crq1, crq2, crq3);

  unsigned long elapsedTime = currentTime - experimentStartTime;

#if OUTPUT_CSV
  Serial.print("D,");
  Serial.print(elapsedTime);
  Serial.print(",");
  Serial.print(extensionAngle, 3);
  Serial.print(",");
  Serial.print(crq0, 6);
  Serial.print(",");
  Serial.print(crq1, 6);
  Serial.print(",");
  Serial.print(crq2, 6);
  Serial.print(",");
  Serial.println(crq3, 6);
#else
  Serial.print("TIME_US: ");
  Serial.print(elapsedTime);
  Serial.print(" | KNEE_EXTENSION_DEG: ");
  Serial.print(extensionAngle, 2);
  Serial.print(" | REL_Q: ");
  Serial.print(crq0, 4);
  Serial.print(",");
  Serial.print(crq1, 4);
  Serial.print(",");
  Serial.print(crq2, 4);
  Serial.print(",");
  Serial.println(crq3, 4);
#endif

  delay(20);   // ~50 Hz
}

