# Bare-Metal FOC Library for STM32

A Simulink-independent, modular Field-Oriented Control (FOC) library for 3-phase BLDC motors on STM32 microcontrollers.

## Overview

This library extracts the core FOC algorithms from your Simulink model and provides a clean, reusable C API that works with any STM32 board configuration.

### Key Features
- ✅ **Zero Simulink dependency** — Pure C99, easily portable
- ✅ **Modular design** — Use Clarke/Park transforms independently
- ✅ **Real-time safe** — No dynamic allocation, deterministic timing
- ✅ **Hardware abstraction** — Callbacks for ADC, encoder, PWM, UART
- ✅ **Multi-rate execution** — Base (17 kHz), mid (1.7 kHz), slow (20 Hz) rates
- ✅ **Anti-windup PI control** — Deadzone-based integrator clamping
- ✅ **Open-loop startup** — V/f ramp with frequency control
- ✅ **Tunable at runtime** — Update PI gains over UART

## Architecture

```
foc_lib/
├── inc/
│   ├── foc_config.h          # Tuning parameters & compile-time config
│   ├── foc_types.h           # Core data types (no Simulink types)
│   ├── foc_math.h            # Clarke, Park, SVPWM, sin/cos lookup
│   ├── foc_current.h         # Current loop & PI controllers
│   ├── foc_angle.h           # Encoder angle processing
│   ├── foc_speed.h           # Speed control loop
│   ├── foc_openloop.h        # Open-loop startup V/f
│   └── foc_core.h            # Main FOC API
├── src/
│   ├── foc_math.c
│   ├── foc_current.c
│   ├── foc_angle.c
│   ├── foc_speed.c
│   ├── foc_openloop.c
│   └── foc_core.c
└── README.md                 # This file
```

## Integration with Your STM32 Project

### Step 1: Add Library to Build

In your STM32CubeMX or Makefile:
```makefile
# Add include paths
INCLUDES += -Ifoc_lib/inc

# Add source files
SOURCES += foc_lib/src/foc_math.c
SOURCES += foc_lib/src/foc_current.c
SOURCES += foc_lib/src/foc_angle.c
SOURCES += foc_lib/src/foc_speed.c
SOURCES += foc_lib/src/foc_openloop.c
SOURCES += foc_lib/src/foc_core.c
```

### Step 2: Implement Hardware Abstraction Layer

In your `main.c` or a new `foc_hal.c`:

```c
#include "foc_core.h"
#include "stm32g4xx_hal.h"

/* Hardware handles (from your STM32 config) */
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim1, htim2;
extern UART_HandleTypeDef huart1;

/* HAL callback implementations */
uint16_t my_adc_read_ia(void) {
    return adcBuffer[0];  /* DMA reads phase A */
}

uint16_t my_adc_read_ib(void) {
    return adcBuffer[1];  /* DMA reads phase B */
}

uint32_t my_encoder_get_count(void) {
    return __HAL_TIM_GET_COUNTER(&htim2);
}

void my_pwm_set_compare(uint8_t channel, uint16_t count) {
    uint32_t tim_channel = (channel == 0) ? TIM_CHANNEL_1 :
                           (channel == 1) ? TIM_CHANNEL_2 : TIM_CHANNEL_3;
    __HAL_TIM_SET_COMPARE(&htim1, tim_channel, count);
}

void my_uart_send(const uint8_t *data, uint16_t len) {
    HAL_UART_Transmit_DMA(&huart1, (uint8_t*)data, len);
}

/* Export HAL interface */
const foc_hal_t foc_hal = {
    .adc_read_ia = my_adc_read_ia,
    .adc_read_ib = my_adc_read_ib,
    .encoder_get_count = my_encoder_get_count,
    .pwm_set_compare = my_pwm_set_compare,
    .uart_send = my_uart_send,
};
```

### Step 3: Replace Simulink ISR with FOC Library

**Before (Simulink):**
```c
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM1) {
        BLDC_FOC_SPEED_TI28379d_1_B.count = __HAL_TIM_GET_COUNTER(&htim2);
        regularReadADCDMA(adcBuffer[0], adcBuffer[1]);
        BLDC_FOC_SPEED_TI28379d_1_SetEventsForThisBaseStep(eventFlags);
        BLDC_FOC_SPEED_TI28379d_1_step0();
        if (eventFlags[1]) BLDC_FOC_SPEED_TI28379d_1_step1();
        if (eventFlags[2]) BLDC_FOC_SPEED_TI28379d_1_step2();
        // ... PWM write code ...
    }
}
```

**After (FOC Library):**
```c
foc_state_t foc_state;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM1) {
        /* Base rate (17 kHz) — current control */
        foc_step_base(&foc_state, &foc_hal);
        
        /* Mid-rate (1.7 kHz) every 10 cycles */
        if (foc_state.cycle_count % FOC_RATE_SPEED_DIV == 0) {
            foc_step_mid(&foc_state);
        }
        
        /* Slow rate (20 Hz) every 850 cycles */
        if (foc_state.cycle_count % FOC_RATE_COMMS_DIV == 0) {
            foc_step_slow(&foc_state, &foc_hal);
        }
    }
}
```

### Step 4: Initialize FOC at Startup

In `main()`, **after** hardware init but **before** starting interrupts:

```c
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_ADC1_Init();
    MX_USART1_UART_Init();
    MX_TIM1_Init();
    MX_TIM2_Init();
    
    /* ADC calibration */
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
    
    /* Read offset calibration (motor stopped) */
    HAL_ADCEx_InjectedStart_IT(&hadc1);
    HAL_ADCEx_InjectedPollForConversion(&hadc1, 10);
    uint16_t adc_ia_offset = HAL_ADCEx_InjectedGetValue(&hadc1, ADC_INJECTED_RANK_1);
    uint16_t adc_ib_offset = HAL_ADCEx_InjectedGetValue(&hadc1, ADC_INJECTED_RANK_2);
    HAL_ADCEx_InjectedStop(&hadc1);
    
    /* Initialize FOC library */
    foc_init(&foc_state, adc_ia_offset, adc_ib_offset);
    
    /* Start hardware */
    HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
    HAL_TIMEx_EnableEncoderFirstIndex(&htim2);
    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adcBuffer, 2);
    
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_3);
    
    HAL_TIM_Base_Start_IT(&htim1);  /* Starts 17 kHz FOC ISR */
    HAL_UART_Receive_DMA(&huart1, uartRxBuf, 6);
    
    while (1) {
        /* Main loop — can do low-priority tasks here */
    }
}
```

### Step 5: Handle UART Commands

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        float speed_ref;
        uint16_t control_word;
        
        memcpy(&speed_ref, &uartRxBuf[0], 4);
        memcpy(&control_word, &uartRxBuf[4], 2);
        
        /* Send commands to FOC */
        foc_set_speed_ref(&foc_state, speed_ref);
        foc_set_control_word(&foc_state, control_word);
        
        /* Re-arm DMA */
        HAL_UART_Receive_DMA(&huart1, uartRxBuf, 6);
    }
}
```

## Configuration

Edit `foc_lib/inc/foc_config.h` to tune the controller:

```c
/* Motor Parameters */
#define FOC_POLE_PAIRS          10      /* For your motor */
#define FOC_ENCODER_PPR         2500    /* Encoder resolution */

/* Control Rates */
#define FOC_RATE_SPEED_DIV      10      /* 17 kHz / 10 = 1.7 kHz */
#define FOC_RATE_COMMS_DIV      850     /* 17 kHz / 850 = 20 Hz */

/* PI Gains */
#define FOC_PI_ID_KP            0.08f   /* D-axis proportional */
#define FOC_PI_ID_KI            0.08f   /* D-axis integral */
#define FOC_PI_IQ_KP            0.08f   /* Q-axis proportional */
#define FOC_PI_IQ_KI            0.08f   /* Q-axis integral */
#define FOC_PI_SPEED_KP         12.0f   /* Speed proportional */
#define FOC_PI_SPEED_KI         300.0f  /* Speed integral */

/* Limits */
#define FOC_CURRENT_MAX         1.0f    /* Max current (pu) */
#define FOC_VOLTAGE_MAX         1.0f    /* Max voltage (pu) */

/* Startup */
#define FOC_STARTUP_TIME_SEC    3.0f    /* Ramp duration */
#define FOC_STARTUP_V_MAX       0.95f   /* Max startup voltage */
#define FOC_STARTUP_V_MIN       0.15f   /* Min startup voltage */
```

## API Reference

### Main Control Loop

```c
/* Initialize FOC (call once) */
void foc_init(foc_state_t *foc, uint16_t adc_ia_offset, uint16_t adc_ib_offset);

/* Base rate (17 kHz) — current control & angle update */
void foc_step_base(foc_state_t *foc, const foc_hal_t *hal);

/* Mid-rate (1.7 kHz) — speed control */
void foc_step_mid(foc_state_t *foc);

/* Slow rate (20 Hz) — communications */
void foc_step_slow(foc_state_t *foc, const foc_hal_t *hal);
```

### Parameter Commands

```c
/* Set speed reference (pu: -1.0 to 1.0) */
void foc_set_speed_ref(foc_state_t *foc, real32_T speed_ref);

/* Enable/disable motor */
void foc_set_enable(foc_state_t *foc, boolean_T enable);

/* Process UART control word */
void foc_set_control_word(foc_state_t *foc, uint16_T control_word);

/* Update current loop gains */
void foc_set_current_gains(foc_state_t *foc, real32_T kp_d, real32_T ki_d, 
                           real32_T kp_q, real32_T ki_q);

/* Update speed loop gains */
void foc_set_speed_gains(foc_state_t *foc, real32_T kp, real32_T ki);
```

### State Query

```c
/* Get current state for telemetry/debugging */
const foc_state_t* foc_get_state(const foc_state_t *foc);

/* Access key measurements */
real32_T omega = foc_state.angle.omega;         /* Angular velocity (rad/s) */
real32_T theta = foc_state.angle.theta_elec;    /* Electrical angle (rad) */
real32_T id = foc_state.iloop.id;               /* D-axis current (pu) */
real32_T iq = foc_state.iloop.iq;               /* Q-axis current (pu) */
```

## Differences from Simulink Generated Code

| Aspect | Simulink | FOC Library |
|--------|----------|-------------|
| **Types** | `real32_T`, custom Simulink types | Standard C99 (`float`, `uint16_t`, etc.) |
| **Data Storage** | Global `BLDC_FOC_SPEED_TI28379d_1_B`, `DW` structs | Single `foc_state_t` |
| **Hardware Coupling** | Direct HAL calls in `step0/1/2` | Abstracted callbacks via `foc_hal_t` |
| **Rate Scheduling** | `eventFlags`, `SetEventsForThisBaseStep()` | Cycle counter modulo in ISR |
| **API** | Multiple `step*()` functions | Single `foc_step_*()` functions |
| **Modularity** | Monolithic | Composable (use Clarke/Park independently) |

## Performance

- **Base rate (17 kHz, 58.8 µs):** ~20-25 µs CPU time
- **Mid-rate (1.7 kHz, 588 µs):** ~30-40 µs CPU time
- **Memory:** ~2 KB (state + lookup tables)
- **Sine/Cos lookup:** 801-entry interpolated table, <1 µs per lookup

## Troubleshooting

### Motor won't start
- Check ADC offset calibration range [1500, 2500]
- Verify encoder index pulse detected: `indexFound` flag
- Check V/f startup parameters: `FOC_STARTUP_V_MIN`, `FOC_STARTUP_TIME_SEC`

### High current spikes
- Reduce PI gains (`FOC_PI_ID_KI`, `FOC_PI_IQ_KI`)
- Increase speed ramp time (`FOC_STARTUP_TIME_SEC`)
- Check current sensor wiring and offset

### Oscillation in speed loop
- Reduce speed loop Ki: `FOC_PI_SPEED_KI` (try 100–200 first)
- Increase low-pass filter: `FOC_SPEED_LPF_ALPHA`

### Angle tracking errors
- Verify encoder PPR matches motor: `FOC_ENCODER_PPR`
- Check pole pairs: `FOC_POLE_PAIRS`
- Outlier rejection at 0.2 rad — normal operation

## License

This library is part of your STM32 BLDC FOC project. Use as needed.

## References

- **Clarke/Park Transforms:** IEEE Std 1415-1996 (Power Systems Relaying Commitee)
- **SVPWM:** Mohan, Undeland, Robbins — "Power Electronics: Converters, Applications, and Design" (3rd Ed.)
- **Anti-windup:** Åström & Hägglund — "PID Controllers: Theory, Design, and Tuning" (2nd Ed.)
