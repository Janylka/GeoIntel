def main() -> None:
    """Placeholder script for cropland mask ingestion."""
    print("SKIPPING: Cropland mask ingestion (ingest_cropland_mask.py).")
    print("This is a placeholder. The full implementation will use Google Earth Engine.")
    # In a real scenario, this script would connect to GEE,
    # load the ESA WorldCover image, and compute cropland area for each admin unit,
    # then update the `cropland_ha` column in the `admin_unit` table.


if __name__ == "__main__":
    main()
