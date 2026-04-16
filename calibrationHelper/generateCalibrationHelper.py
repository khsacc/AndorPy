import sys
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

# Peak detection constants - modify these values if needed
DEFAULT_PROMINENCE_RATIO = 0.01  # 1% of max intensity
DEFAULT_HEIGHT_RATIO = 0.02      # 2% of max intensity
DEFAULT_DISTANCE = 5            # Minimum pixels between peaks

def gaussian(x, amp, cen, wid, off):
    return amp * np.exp(-(x - cen)**2 / (2 * wid**2)) + off

def fit_peak(x, y, peak_idx, window=10):
    start = max(0, peak_idx - window)
    end = min(len(x), peak_idx + window)
    x_sub = x[start:end]
    y_sub = y[start:end]
    p0 = [np.max(y_sub) - np.min(y_sub), x[peak_idx], 1.0, np.min(y_sub)]
    try:
        popt, _ = curve_fit(gaussian, x_sub, y_sub, p0=p0)
        return popt[1] 
    except:
        return x[peak_idx]

def main():
    if len(sys.argv) < 2:
        print("Usage: python generateCalibrationHelper.py <input_file.txt>")
        return

    input_file = sys.argv[1]
    
    # User Input for Metadata
    material_name = input("Enter Reference Material Name: ").strip()
    wave_range = input("Enter Approximate Wavelength Range: ").strip()
    ref_url = input("Enter Reference URL (Optional): ").strip()

    # Data Loading
    pixels = []
    counts = []
    try:
        with open(input_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split(',')
                if len(parts) == 2:
                    pixels.append(float(parts[0]))
                    counts.append(float(parts[1]))
    except Exception as e:
        print(f"Error: {e}")
        return

    pixels = np.array(pixels)
    counts = np.array(counts)
    max_val = np.max(counts)

    # Automatic Peak Detection
    peak_indices, _ = find_peaks(
        counts, 
        prominence = max_val * DEFAULT_PROMINENCE_RATIO, 
        height = max_val * DEFAULT_HEIGHT_RATIO,
        distance = DEFAULT_DISTANCE 
    )
    
    fitted_pixels = []
    for idx in peak_indices:
        precise_pixel = fit_peak(pixels, counts, idx)
        fitted_pixels.append(precise_pixel)
    
    fitted_pixels = np.array(fitted_pixels)
    print(f"\nFound {len(fitted_pixels)} peaks using pre-defined thresholds.")
    
    # Interaction Setup
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(pixels, counts, label='Raw Data', color='black', lw=0.8)
    for i, p in enumerate(fitted_pixels):
        ax.axvline(p, color='red', linestyle='--', alpha=0.3)
        ax.text(p, counts[int(p)] if int(p) < len(counts) else max_val, str(i), 
                color='blue', fontsize=10, fontweight='bold', ha='center')
    ax.set_title(f"Peak Identification: {material_name}")
    ax.set_xlabel("Pixel")
    ax.set_ylabel("Intensity")
    plt.grid(True, alpha=0.3)
    plt.show()

    selected_pixel_coords = []
    lit_wavelengths = []

    while True:
        user_input = input("\nEnter [Peak ID, Lit Wavelength] (or 'q' to finish): ")
        
        if user_input.lower() == 'q':
            if len(selected_pixel_coords) < 3:
                print(f"Current points: {len(selected_pixel_coords)}")
                print("Error: At least 3 points are required for quadratic fitting.")
                confirm = input("Do you want to (c)ontinue input or (a)bort? [c/a]: ").lower()
                if confirm == 'a':
                    print("Aborted.")
                    return
                continue
            else:
                confirm = input(f"Proceed with {len(selected_pixel_coords)} points? [y/n]: ").lower()
                if confirm == 'y':
                    break
                continue
        
        try:
            idx_str, wave_str = user_input.split(',')
            idx = int(idx_str)
            wave = float(wave_str)
            if 0 <= idx < len(fitted_pixels):
                selected_pixel_coords.append(fitted_pixels[idx])
                lit_wavelengths.append(wave)
                print(f"Added: {fitted_pixels[idx]:.2f} pix -> {wave} nm")
            else:
                print("Index out of range.")
        except:
            print("Invalid format. Use 'ID, Wavelength'.")

    # Calibration Calculation
    coeffs = np.polyfit(selected_pixel_coords, lit_wavelengths, 2)
    poly_func = np.poly1d(coeffs)
    calibrated_wavelengths = poly_func(pixels)

    # JSON Export
    output_data = {
        "material": material_name,
        "approximate_range": wave_range,
        "reference_url": ref_url,
        "spectrum": {
            "wavelength": calibrated_wavelengths.tolist(),
            "intensity": counts.tolist()
        },
        "reference_peaks": [
            {"calibrated": float(poly_func(p)), "literature": float(l)} 
            for p, l in zip(selected_pixel_coords, lit_wavelengths)
        ]
    }

    output_filename = f"{material_name}_{wave_range}_reference.json".replace(" ", "_")
    with open(output_filename, 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"\nSaved: {output_filename}")
    
    # Final Visualization
    plt.ioff()
    plt.close('all')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    plt.subplots_adjust(hspace=0.3)

    # Plot 1: Calibrated Spectrum
    ax1.plot(calibrated_wavelengths, counts, color='black', lw=1)
    ax1.scatter(lit_wavelengths, [max_val]*len(lit_wavelengths), color='red', marker='v', label='Lit. Peaks')
    ax1.set_title("Calibrated Spectrum")
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Intensity")
    ax1.grid(True, alpha=0.3)

    # Plot 2: Calibration Curve
    pix_range = np.linspace(min(pixels), max(pixels), 100)
    ax2.plot(pix_range, poly_func(pix_range), color='blue', label='Fit')
    ax2.scatter(selected_pixel_coords, lit_wavelengths, color='red', label='Selected')
    ax2.set_title("Calibration Curve (Pixel vs Wavelength)")
    ax2.set_xlabel("Pixel Index")
    ax2.set_ylabel("Wavelength (nm)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.show()

if __name__ == "__main__":
    main()