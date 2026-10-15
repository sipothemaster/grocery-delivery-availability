# Data requirements

The crawler accepts normalized or unnormalized UK postcodes from a CSV file.
It does not bundle postcode, centroid, boundary, or study output data.

The associated study's postcode-quality audit used:

- OS Code-Point Open dataset version `2026.3.0`, copyright/update metadata July
  2026;
- LSOA 2021 population-weighted centroids for England and Wales;
- Data Zone 2022 population-weighted centroids for Scotland.

For historical or superseded representative postcodes, the study selected
current Code-Point units with positional quality `PQ <= 50`, ranked by
Euclidean British National Grid distance from the population-weighted
centroid. Candidate selection did not use retailer outcomes.

Record the exact source, version, download date, licence, and checksum of every
external data input used with a published analysis. Publish derived research
data separately from the software release.

