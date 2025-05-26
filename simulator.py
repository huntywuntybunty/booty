import numpy as np

def simulate_ks(adjusted_mean: float, base_ip: float, scaled_ip: float, n: int = 20000) -> np.ndarray:
    """
    Simulate strikeouts using opponent-adjusted innings pitched and per-inning K rate.
    """
    if adjusted_mean <= 0 or base_ip <= 0 or scaled_ip <= 0:
        return np.zeros(n)

    # Derive K rate per inning based on original expected K mean and historical IP
    k_rate_per_inning = adjusted_mean / base_ip

    # Simulate innings pitched from a normal distribution centered at scaled IP
    ip_samples = np.random.normal(loc=scaled_ip, scale=1.0, size=n)
    ip_samples = np.clip(ip_samples, 3.0, 8.0)  # IP realistically between 3–8

    ks_samples = []
    for ip in ip_samples:
        ks = 0
        full = int(ip)
        frac = ip % 1

        for _ in range(full):
            ks += np.random.poisson(k_rate_per_inning)
        if frac > 0:
            ks += np.random.poisson(k_rate_per_inning * frac)

        ks_samples.append(ks)

    return np.array(ks_samples)
