import sys
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

def gaussian(x, amp, cen, wid, off):
    """Gaussian function for peak fitting."""
    return amp * np.exp(-(x - cen)**2 / (2 * wid**2)) + off

def fit_peak(x, y, peak_idx, window=10):
    """Perform gaussian fitting to find sub-pixel peak center."""
    start = max(0, peak_idx - window)
    end = min(len(x), peak_idx + window)
    x_sub = x[start:end]
    y_sub = y[start:end]
    
    # Initial guess: [amplitude, center, width, offset]
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
    
    # 1. User Input for Metadata
    material_name = input("Enter Reference Material Name (e.g., HgAr): ").strip()
    wave_range = input("Enter Approximate Wavelength Range (e.g., 400-900nm): ").strip()

    # 2. Data Loading
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
        print(f"Error reading file: {e}")
        return

    pixels = np.array(pixels)
    counts = np.array(counts)

    # 3. Peak Detection and Fitting
    # Adjust prominence based on your noise level
    peak_indices, _ = find_peaks(counts, prominence=np.max(counts)*0.05)
    
    fitted_pixels = []
    for idx in peak_indices:
        precise_pixel = fit_peak(pixels, counts, idx)
        fitted_pixels.append(precise_pixel)
    
    fitted_pixels = np.array(fitted_pixels)

    # 4. Interactive Peak Selection
    print("\n--- Peak Selection Mode ---")
    print("Check the plot window and map peak IDs to literature values.")
    
    plt.ion() # Interaction ON
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(pixels, counts, label='Raw Data', color='gray', alpha=0.7)
    
    for i, p in enumerate(fitted_pixels):
        ax.axvline(p, color='red', linestyle='--', alpha=0.5)
        ax.text(p, np.max(counts), str(i), color='red', fontsize=12, fontweight='bold', ha='center')
    
    ax.set_title(f"Spectrum: {material_name}")
    ax.set_xlabel("Pixel")
    ax.set_ylabel("Intensity")
    plt.show()

    selected_pixel_coords = []
    lit_wavelengths = []

    while True:
        user_input = input("Enter [Peak ID, Lit Wavelength] (e.g., 1, 435.83) or 'q' to finish: ")
        if user_input.lower() == 'q':
            if len(selected_pixel_coords) < 3:
                print("Error: Need at least 3 points for quadratic fitting.")
                continue
            break
        
        try:
            idx_str, wave_str = user_input.split(',')
            idx = int(idx_str)
            wave = float(wave_str)
            
            if 0 <= idx < len(fitted_pixels):
                selected_pixel_coords.append(fitted_pixels[idx])
                lit_wavelengths.append(wave)
                print(f"Added: Pixel {fitted_pixels[idx]:.2f} -> {wave} nm")
            else:
                print("Invalid Index.")
        except ValueError:
            print("Invalid format. Please use 'ID, Wavelength'.")

    # 5. Calibration (2nd order polynomial fit)
    coeffs = np.polyfit(selected_pixel_coords, lit_wavelengths, 2)
    poly_func = np.poly1d(coeffs)
    
    calibrated_wavelengths = poly_func(pixels)
    calibrated_peak_positions = poly_func(np.array(selected_pixel_coords))

    # 6. JSON Export
    output_data = {
        "material": material_name,
        "approximate_range": wave_range,
        "spectrum": {
            "wavelength": calibrated_wavelengths.tolist(),
            "intensity": counts.tolist()
        },
        "reference_peaks": [
            {"calibrated": float(c), "literature": float(l)} 
            for c, l in zip(calibrated_peak_positions, lit_wavelengths)
        ]
    }

    output_filename = f"{material_name}_{wave_range}_reference.json".replace(" ", "_").replace("/", "-")
    with open(output_filename, 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"\nCalibration complete. File saved as: {output_filename}")
    
    # Final Verification Plot
    plt.ioff()
    plt.close()
    plt.figure(figsize=(10, 6))
    plt.plot(calibrated_wavelengths, counts)
    plt.scatter(lit_wavelengths, [np.max(counts)]*len(lit_wavelengths), color='red', marker='v', label='Ref Peaks')
    plt.title("Calibrated Spectrum")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    main()