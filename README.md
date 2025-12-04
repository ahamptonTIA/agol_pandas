# agol_pandas

A small helper package for using pandas with ArcGIS Online feature layers.

## Summary

agol_pandas provides simple helpers to convert ArcGIS Online feature layers to pandas DataFrames and back, making it easier to use pandas for data analysis and to push updates back to AGOL.

## Installation

Install directly from the repository:

```bash
pip install git+https://github.com/ahamptonTIA/agol_pandas.git
```

## Quick example

```python
from arcgis.gis import GIS
import agol_pandas

gis = GIS("home")  # or GIS("url", "username", "password")
item = gis.content.get("YOUR_ITEM_ID")
layer = item.layers[0]

# Read a feature layer into a pandas DataFrame
df = agol_pandas.read_feature_layer(layer)

# Do pandas work...
df["new_col"] = df["existing_col"] * 2

# Write the DataFrame back to AGOL (update or replace)
agol_pandas.to_feature_layer(df, layer, mode="update")
```

Note: Replace the example function names above with the actual helper names from the package (read_feature_layer, to_feature_layer, etc.) if they differ.

## Features

- Convert AGOL FeatureLayer -> pandas.DataFrame
- Convert pandas.DataFrame -> AGOL FeatureLayer (create/update)
- Preserve attribute fields and basic geometry where possible

## Contributing

Contributions and bug reports are welcome. Please open issues or pull requests in the repository.

## License

MIT License
```
