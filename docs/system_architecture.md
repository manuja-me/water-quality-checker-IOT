# System Architecture & Technical Diagrams

## 1. Top-Level Hardware & Software Architecture

```mermaid
flowchart TD
    subgraph TxNode ["Tx Illumination Node (ESP32)"]
        TxClock["FreeRTOS Timer (80 Hz)"] --> TxPayload["ESP-NOW / 802.11 Frame Generator"]
        TxPayload --> TxRF["2.4 GHz RF Power Amplifier"]
    end

    TxRF -.->|"Multipath RF Waves\n(Through Wall / Obstacle)"| Channel["Sensing Medium\n(Wall / Monitored Room)"]
    Channel -.-> RxAntenna["Rx Antenna"]

    subgraph RxNode ["Rx Edge Node (Custom PCB)"]
        RxAntenna --> Baseband["Wi-Fi Baseband Demodulator"]
        Baseband --> CSICallback["esp_wifi_set_csi_rx_cb()"]
        
        subgraph EdgeDSP ["Embedded DSP Engine (C)"]
            CSICallback --> AmpExtract["Amplitude Extraction\n|H_k| = sqrt(I_k^2 + Q_k^2)"]
            AmpExtract --> SlideBuffer["Circular Sliding Window (N=40)"]
            SlideBuffer --> VarianceCalc["Window Variance V(t)"]
            VarianceCalc --> EMACalc["Exponential Moving Average S(t)"]
            EMACalc --> SchmittTrigger["Hysteresis Dual Threshold\n(High=18.5, Low=8.0)"]
        end
        
        SchmittTrigger -->|"GPIO 26"| Relay["5V Optocoupled Relay"]
        SchmittTrigger -->|"GPIO 27"| Buzzer["2N2222 + 5V Piezo Buzzer"]
        SchmittTrigger -->|"GPIO 25"| AlertLED["Red Alert LED"]
        CSICallback -->|"GPIO 33"| LinkLED["Green Link Heartbeat LED"]

        subgraph PowerSystem ["Power & Backup Supply"]
            Mains["5V USB / DC In"] --> D1["1N5819 (D1)"]
            Mains --> TP4056["TP4056 Charger"]
            TP4056 --> Batt["18650 3.7V Li-ion"]
            Batt --> MT3608["MT3608 Boost (4.8V)"]
            MT3608 --> D2["1N5819 (D2)"]
            D1 --> PowerRail["Switched 5V Rail"]
            D2 --> PowerRail
            PowerRail --> LDO["AMS1117 3.3V LDO"]
        end
    end

    SchmittTrigger -->|"UART Serial ($CSI Frame)"| HostLaptop["Linux Laptop Host"]

    subgraph Dashboard ["Host Visualizer (Python / Web)"]
        HostLaptop --> SSE["Server-Sent Events Stream"]
        SSE --> RadarUI["HTML5 Canvas Radar View"]
        SSE --> ChartUI["Real-time Variance Graph"]
        SSE --> GaugeUI["Movement Intensity Gauge"]
    end
```

---

## 2. Mathematical Signal Processing Formulation

### 2.1 Subcarrier Amplitude Extraction
For each received packet on Channel 6, the Wi-Fi baseband provides a complex CSI vector $H$:
$$H_k = I_k + j Q_k \quad (k \in [0, N_{sub}-1])$$
The amplitude of subcarrier $k$ is calculated as:
$$A_k = \sqrt{I_k^2 + Q_k^2}$$
The mean amplitude across subcarriers for packet $t$ is:
$$\bar{A}(t) = \frac{1}{K} \sum_{k=1}^K A_k$$

### 2.2 Sliding Window Variance
A circular FIFO buffer maintains the last $N = 40$ mean amplitude samples:
$$\mu(t) = \frac{1}{N} \sum_{i=0}^{N-1} \bar{A}(t - i)$$
$$V(t) = \frac{1}{N} \sum_{i=0}^{N-1} \left( \bar{A}(t - i) - \mu(t) \right)^2$$

### 2.3 Exponential Moving Average (EMA)
To eliminate spurious impulse noise without introducing phase delay:
$$S(t) = \alpha \cdot V(t) + (1 - \alpha) \cdot S(t - 1) \quad (\alpha = 0.25)$$

### 2.4 Hysteresis Dual-Threshold Decision Rule
Let $T_{\text{high}} = 18.5$, $T_{\text{low}} = 8.0$, and holdoff time $\tau_{\text{hold}} = 1.5\,\text{s}$:
$$\text{State}(t) = \begin{cases} 
\text{TRUE (Movement)}, & \text{if } S(t) \ge T_{\text{high}} \\
\text{TRUE (Hold)}, & \text{if } S(t) > T_{\text{low}} \text{ and } (t - t_{\text{trigger}}) < \tau_{\text{hold}} \\
\text{FALSE (Quiet)}, & \text{if } S(t) < T_{\text{low}} \text{ and } (t - t_{\text{trigger}}) \ge \tau_{\text{hold}}
\end{cases}$$
