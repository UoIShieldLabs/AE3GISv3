import psm
import time

time_delta = 0.1

attack_enabled = True

display_min_rpm = 2990        # fake RPM lower bound shown to PLC/HMI
display_max_rpm = 3000        # fake RPM upper bound shown to PLC/HMI
display_target_rpm = display_max_rpm
actual_min_rpm = 900          # real RPM lower bound
actual_max_rpm = 10000        # real RPM upper bound
actual_target_rpm = actual_max_rpm

display_ramp_rpm_per_s = 500.0
actual_ramp_rpm_per_s = 800.0

def ramp_rpm(current_rpm, target_rpm, dt, ramp_rate_rpm_per_s):
    max_delta = ramp_rate_rpm_per_s * dt
    error = target_rpm - current_rpm

    if abs(error) <= max_delta:
        return int(target_rpm)

    if error > 0:
        return int(current_rpm + max_delta)
    else:
        return int(current_rpm - max_delta)

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
    global actual_target_rpm, display_target_rpm

    motor_running = psm.get_var("QX0.1")
    plc_target_freq = psm.get_var("QW0")

    current_display_rpm = psm.get_var("IW0")
    current_actual_rpm = psm.get_var("IW1")

    if not motor_running:
        # ramp both down smoothly when motor stops
        display_rpm = ramp_rpm(
            current_rpm=current_display_rpm,
            target_rpm=0,
            dt=time_delta,
            ramp_rate_rpm_per_s=display_ramp_rpm_per_s
        )

        actual_rpm = ramp_rpm(
            current_rpm=current_actual_rpm,
            target_rpm=0,
            dt=time_delta,
            ramp_rate_rpm_per_s=actual_ramp_rpm_per_s
        )

    else:
        if attack_enabled:
            # fake displayed value oscillates slightly between 2990 and 3000
            if current_display_rpm >= display_max_rpm:
                display_target_rpm = display_min_rpm
            elif current_display_rpm <= display_min_rpm:
                display_target_rpm = display_max_rpm

            display_rpm = ramp_rpm(
                current_rpm=current_display_rpm,
                target_rpm=display_target_rpm,
                dt=time_delta,
                ramp_rate_rpm_per_s=display_ramp_rpm_per_s
            )

            # actual hidden value oscillates between 900 and 10000
            if current_actual_rpm >= actual_max_rpm:
                actual_target_rpm = actual_min_rpm
            elif current_actual_rpm <= actual_min_rpm:
                actual_target_rpm = actual_max_rpm

            actual_rpm = ramp_rpm(
                current_rpm=current_actual_rpm,
                target_rpm=actual_target_rpm,
                dt=time_delta,
                ramp_rate_rpm_per_s=actual_ramp_rpm_per_s
            )
        else:
            # normal mode: both follow VFD behavior
            actual_rpm, _ = vfd_to_motor_rpm(
                vfd_freq_hz=plc_target_freq,
                current_rpm=current_actual_rpm
            )

            display_rpm = actual_rpm

    # Write values back into PLC memory
    psm.set_var("IW0", display_rpm)   # motor_rpm
    psm.set_var("IW1", actual_rpm)    # stuxnet_rpm

def update_outputs():
    pass

if __name__ == "__main__":
    hardware_init()
    while not psm.should_quit():
        update_inputs()
        update_outputs()
        time.sleep(time_delta)
    psm.stop()
