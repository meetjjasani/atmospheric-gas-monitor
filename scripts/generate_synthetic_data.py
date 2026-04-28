import os
import random
from datetime import datetime, timedelta
from pathlib import Path

def generate_synthetic_data(base_path: str, year: int = 2026):
    """Generate 10 months of synthetic CRDS data in Year/Month/Day format."""
    root = Path(base_path) / str(year)
    
    # Months 1 to 10
    for month in range(1, 11):
        month_str = f"{month:02d}"
        month_dir = root / month_str
        
        # 2 days per month (1st and 15th)
        for day in [1, 15]:
            day_str = f"{day:02d}"
            day_dir = month_dir / day_str
            day_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"CFKADS-{year}{month_str}{day_str}-000000Z-DataLog_User_Sync.dat"
            filepath = day_dir / filename
            
            with open(filepath, "w") as f:
                # Header
                header = "DATE                      TIME                      CO_sync                   CO2_sync                  CH4_sync"
                f.write(header + "\n")
                
                # Data (every hour for 24 hours)
                current_date = datetime(year, month, day)
                for hour in range(24):
                    time_str = f"{hour:02d}:00:00.000"
                    date_str = current_date.strftime("%Y-%m-%d")
                    
                    # Random plausible values
                    co = 0.2 + random.random() * 0.3
                    co2 = 410 + random.random() * 40
                    ch4 = 1.9 + random.random() * 0.6
                    
                    row = f"{date_str:<25} {time_str:<25} {co:<25.8f} {co2:<25.8f} {ch4:<25.8f}"
                    f.write(row + "\n")
                    
    print(f"Synthetic data generated at: {base_path}")

if __name__ == "__main__":
    generate_synthetic_data("synthetic_test_data")
