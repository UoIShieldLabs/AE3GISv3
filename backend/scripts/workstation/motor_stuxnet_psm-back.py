import psm
import time

time_delta = 0.1
attack_high_freq = 120
attack_low_freq = 0
attack_enabled = True
attack_state = "high"

def vfd_to_motor_rpm(
    vfd_freq_hz,
    current_rpm,
    dt=time_delta,
    ramp_rate_hz_per_s=5.0,
    poles=4,
    load_torque=0.5,
    rated_torque=1.0,
    rated_slip_percent=3.0
):
    slip = rated_slip_percent * (load_torque / rated_torque)

    if current_rpm > 0:
        current_vfd_freq = (current_rpm * poles) / (120 * (1 - (slip / 100)))
    else:
        current_vfd_freq = 0.0

    freq_err = vfd_freq_hz - current_vfd_freq
    max_delta = ramp_rate_hz_per_s * dt

    if abs(freq_err) > max_delta:
        current_vfd_freq += max_delta if freq_err > 0 else -max_delta
    else:
        current_vfd_freq = vfd_freq_hz

    sync_speed_rpm = (current_vfd_freq * 120) / poles
    actual_rpm = sync_speed_rpm * (1 - slip / 100.0)

    return int(actual_rpm), float(current_vfd_freq)

def hardware_init():
    psm.start()
    print("Start Successful")

def update_inputs():
    global attack_state

    motor_running = psm.get_var("QX0.1")
    displayed_rpm = psm.get_var("IW0")
    plc_target_freq = psm.get_var("QW0")

    if not motor_running:
        commanded_freq = 0
    else:
        if attack_enabled:
            if attack_state == "high":
                commanded_freq = attack_high_freq
            else:
                commanded_freq = attack_low_freq
        else:
            commanded_freq = plc_target_freq

    actual_rpm, current_freq = vfd_to_motor_rpm(
        vfd_freq_hz=commanded_freq,
        current_rpm=displayed_rpm
    )

    # actual / hidden
    psm.set_var("IW1", actual_rpm)

    # reported to PLC/HMI
    psm.set_var("IW0", actual_rpm)

    if current_freq >= attack_high_freq:
        attack_state = "low"
        print("switch off")
    elif current_freq <= 0.5:
        attack_state = "high"
        print("switch on")

def update_outputs():
    pass

if __name__ == "__main__":
    hardware_init()
    while not psm.should_quit():
        update_inputs()
        update_outputs()
        time.sleep(0.1)
    psm.stop()