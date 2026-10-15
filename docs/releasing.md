# Releasing and citation

## Prepare the release

1. Confirm the same version appears in `pyproject.toml`, `CITATION.cff`,
   `src/grocery_delivery_availability/__init__.py`, and `CHANGELOG.md`.
2. Confirm `CITATION.cff` contains the intended release date and only the
   agreed software authors.
3. Run the offline checks and build both distribution formats:

   ```bash
   python -m pip install -e ".[dev,release]"
   python -m ruff check .
   python -m pytest
   python -m build
   ```

4. Inspect the wheel and source distribution. They must contain source,
   documentation, licence, authorship, provenance, changelog, and citation
   metadata, but no research data, collected responses, cookies, browser
   profiles, credentials, screenshots, or operational logs.
5. Review the dated live-test records and
   `docs/responsible-data-collection.md`. A retailer that currently blocks a
   bounded check should remain documented as blocked; do not force a new live
   test merely to complete a release checklist.
6. Confirm CI is offline and builds the same wheel and source distribution.

## Publish and archive

1. Push the reviewed source to the public GitHub repository.
2. Before publishing the first GitHub release, connect the repository in the
   Zenodo GitHub settings and enable it for automatic archiving.
3. Create the Git tag matching the software version, for example `v0.1.0`, and
   publish a GitHub release using the matching changelog section.
4. Confirm Zenodo archived the release and issued both a version DOI and a
   concept DOI.
5. Cite the version DOI for the exact software used in an analysis. Add the
   version DOI to `CITATION.cff` in the next maintenance update; do not rewrite
   the already archived release.

Publications should cite the version DOI corresponding to the software
actually used, not only the concept DOI that represents all versions.
