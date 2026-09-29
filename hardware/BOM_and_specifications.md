 JointSense — Bill of Materials

**Project:** AI-Assisted Early Detection System for Osteoarthritis Risk Markers
**System:** JointSense
**Document:** Bill of Materials
**Version:** 1.4
**Currency:** INR (₹)
**Market:** India

---

## 1. Core Electronics

| No. | Component             | Specification / Model                                       | Qty. | Unit Price (₹) | Total (₹) |
| --: | --------------------- | ----------------------------------------------------------- | ---: | -------------: | --------: |
|   1 | Microcontroller       | ESP32 DevKit V1 / ESP32-WROOM-32                            |    1 |           ₹420 |      ₹420 |
|   2 | Processing Unit       | Raspberry Pi 3 Model B, 1 GB RAM                            |    1 |         ₹3,699 |    ₹3,699 |
|   3 | IMU                   | 7Semi BMI270, 6-axis accelerometer + gyroscope, I²C         |    2 |           ₹501 |    ₹1,002 |
|   4 | Force Sensor          | FSR-402, 14.7 mm sensing diameter                           |    4 |           ₹183 |      ₹732 |
|   5 | ADC                   | ADS1115, 16-bit, 4-channel, I²C                             |    1 |           ₹130 |      ₹130 |
|   6 | Contact Microphone    | TE Connectivity CM-01B, PVDF piezo-film contact microphone  |    1 |      ₹7,704.17 | ₹7,704.17 |
|   7 | Operational Amplifier | Texas Instruments OPA1652, dual JFET-input precision op-amp |    1 |           ₹243 |      ₹243 |

**Core Electronics Subtotal: ₹13,930.17**

---

## 2. Analog Front-End Components

| No. | Component            | Specification                           |  Qty. | Estimated Cost |
| --: | -------------------- | --------------------------------------- | ----: | -------------: |
|   8 | Precision Resistors  | 1% tolerance, assorted values           | 1 set |            ₹75 |
|   9 | Capacitors           | Ceramic / electrolytic, assorted values | 1 set |            ₹75 |
|  10 | Rectifier Components | Diodes and supporting components        | 1 set |            ₹50 |

**Analog Front-End Subtotal: ₹200**

---

## 3. Wiring and Prototype Assembly

| No. | Component          | Specification                   |  Qty. | Estimated Cost |
| --: | ------------------ | ------------------------------- | ----: | -------------: |
|  11 | Flexible Wires     | Thin flexible hookup wire       | 1 set |           ₹100 |
|  12 | Pin Headers        | 2.54 mm male/female headers     | 1 set |            ₹50 |
|  13 | Connectors         | Basic JST / terminal connectors | 1 set |            ₹50 |
|  14 | Heat-Shrink Tubing | Assorted sizes                  | 1 set |            ₹50 |
|  15 | Prototype PCB      | General-purpose perfboard       |     1 |            ₹80 |

**Wiring & Assembly Subtotal: ₹330**

---

## 4. Mechanical Components

| No. | Component           | Specification                | Qty. | Estimated Cost |
| --: | ------------------- | ---------------------------- | ---: | -------------: |
|  16 | Insole Base         | Flexible EVA / fabric insole |    1 |           ₹150 |
|  17 | IMU Mounting Straps | Elastic / Velcro straps      |    2 |           ₹100 |

**Mechanical Subtotal: ₹250**

---

## 5. Complete BOM

| No. | Component              |  Qty. | Unit Price |          Total |
| --: | ---------------------- | ----: | ---------: | -------------: |
|   1 | ESP32 DevKit V1        |     1 |       ₹420 |           ₹420 |
|   2 | Raspberry Pi 3 Model B |     1 |     ₹3,699 |         ₹3,699 |
|   3 | BMI270 IMU             |     2 |       ₹501 |         ₹1,002 |
|   4 | FSR-402                |     4 |       ₹183 |           ₹732 |
|   5 | ADS1115                |     1 |       ₹130 |           ₹130 |
|   6 | CM-01B                 |     1 |  ₹7,704.17 |      ₹7,704.17 |
|   7 | OPA1652                |     1 |       ₹243 |           ₹243 |
|   8 | Precision resistor set | 1 set |        ₹75 |            ₹75 |
|   9 | Capacitor set          | 1 set |        ₹75 |            ₹75 |
|  10 | Rectifier components   | 1 set |        ₹50 |            ₹50 |
|  11 | Flexible wires         | 1 set |       ₹100 |           ₹100 |
|  12 | Pin headers            | 1 set |        ₹50 |            ₹50 |
|  13 | Connectors             | 1 set |        ₹50 |            ₹50 |
|  14 | Heat-shrink tubing     | 1 set |        ₹50 |            ₹50 |
|  15 | Prototype PCB          |     1 |        ₹80 |            ₹80 |
|  16 | Insole base            |     1 |       ₹150 |           ₹150 |
|  17 | IMU mounting straps    |     2 |        ₹50 |           ₹100 |
|     | **Total**              |       |            | **₹14,710.17** |

---

## 6. Cost Summary

| Category                     |           Cost |
| ---------------------------- | -------------: |
| Core Electronics             |     ₹13,930.17 |
| Analog Front-End             |           ₹200 |
| Wiring & Assembly            |           ₹330 |
| Mechanical Components        |           ₹250 |
| **Total Estimated BOM Cost** | **₹14,710.17** |

### Recommended Procurement Budget: **₹15,000**

---

## 7. Component Specifications

### ESP32 DevKit V1

| Parameter     | Specification     |
| ------------- | ----------------- |
| Module        | ESP32-WROOM-32    |
| Processor     | Dual-core Xtensa  |
| Maximum Clock | 240 MHz           |
| Logic Voltage | 3.3 V             |
| I²C           | Yes               |
| UART          | Yes               |
| ADC           | Integrated        |
| Wireless      | Wi-Fi + Bluetooth |
| Quantity      | 1                 |

### Raspberry Pi 3 Model B

| Parameter | Specification            |
| --------- | ------------------------ |
| Processor | Broadcom BCM2837         |
| CPU       | Quad-core ARM Cortex-A53 |
| Clock     | 1.2 GHz                  |
| RAM       | 1 GB                     |
| GPIO      | 40-pin                   |
| I²C       | Yes                      |
| UART      | Yes                      |
| USB       | 4 × USB 2.0              |
| Wireless  | Wi-Fi + Bluetooth        |
| Storage   | microSD                  |
| Quantity  | 1                        |

### BMI270

| Parameter     | Specification |
| ------------- | ------------- |
| Sensor        | Bosch BMI270  |
| Type          | 6-axis IMU    |
| Accelerometer | 3-axis        |
| Gyroscope     | 3-axis        |
| Interface     | I²C           |
| Quantity      | 2             |
| Mounting      | Thigh + Shin  |

### FSR-402

| Parameter        | Specification            |
| ---------------- | ------------------------ |
| Sensor           | FSR-402                  |
| Type             | Force-sensitive resistor |
| Sensing Diameter | Approximately 14.7 mm    |
| Output           | Variable resistance      |
| Configuration    | Voltage divider          |
| Quantity         | 4                        |
| Mounting         | Instrumented insole      |

### ADS1115

| Parameter         | Specification |
| ----------------- | ------------- |
| Resolution        | 16-bit        |
| Channels          | 4             |
| Interface         | I²C           |
| PGA               | Programmable  |
| Quantity          | 1             |
| Required Channels | 4             |
| Budgeted Price    | ₹130          |

### CM-01B

| Parameter          | Specification                |
| ------------------ | ---------------------------- |
| Manufacturer       | TE Connectivity              |
| Part Number        | CM-01B                       |
| Order Code         | 2771919                      |
| Sensor Type        | Contact microphone           |
| Sensing Technology | PVDF piezo film              |
| Frequency Response | 8 Hz – 2.2 kHz               |
| Supply Voltage     | 4–30 VDC                     |
| Output             | Buffered analog output       |
| Quantity           | 1                            |
| Application        | Knee vibration / VAG sensing |

**Reference Price:** ₹7,704.17 for one unit.

### OPA1652

| Parameter      | Specification                         |
| -------------- | ------------------------------------- |
| Device         | OPA1652                               |
| Type           | Dual JFET-input operational amplifier |
| Application    | CM-01B analog front-end               |
| Quantity       | 1                                     |
| Budgeted Price | ₹243                                  |

---

## 8. Essential Components

* ESP32 DevKit V1 — **1**
* Raspberry Pi 3 Model B — **1**
* BMI270 — **2**
* FSR-402 — **4**
* ADS1115 — **1**
* CM-01B — **1**
* OPA1652 — **1**
* Precision resistor set — **1**
* Capacitor set — **1**
* Rectifier components — **1 set**
* Flexible wires — **1 set**
* Pin headers/connectors — **1 set**
* Heat-shrink tubing — **1 set**
* Prototype PCB — **1**
* Insole base — **1**
* IMU mounting straps — **2**

---

## 9. Excluded Components

| Component                        | Reason                                                  |
| -------------------------------- | ------------------------------------------------------- |
| Raspberry Pi 4                   | Raspberry Pi 3 is sufficient for the prototype          |
| Dedicated Li-Po battery          | External USB power can be used during prototype testing |
| TP4056 charging module           | Not required with external power                        |
| DC-DC converter                  | Not required with appropriate regulated USB power       |
| Dedicated Raspberry Pi enclosure | Not essential for prototype                             |
| HDMI cable                       | Not required for headless operation                     |
| Dedicated Raspberry Pi PSU       | Existing compatible supply can be used                  |
| Custom PCB                       | Prototype perfboard is sufficient                       |
| Additional ADC                   | One ADS1115 provides four channels                      |
| Additional IMU                   | Two IMUs are sufficient                                 |
| Additional FSR                   | Four FSRs are sufficient                                |

---

## 10. Final Cost

**Estimated Prototype BOM Cost: ₹14,710.17**

**Recommended Procurement Budget: ₹15,000**

**File:** `docs/BOM.md`
**Version:** `1.1`
