"""Typed models for OpenStack API responses (subset used by orca).

Models are TypedDicts with ``total=False`` — the field set we actually
read from each resource, not an exhaustive schema. Adding a field that
mypy starts to flag means widening the type, not silencing the error.
"""
