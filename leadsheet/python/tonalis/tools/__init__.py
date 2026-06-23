"""Offline developer tools for the lead-sheet linter.

Not part of the shipped runtime — these are one-time / maintenance scripts (e.g. the chord
reconciliation oracle builder). They import only stdlib + ``tonalis`` so the import-boundary
guard's ``tonalis.tools`` check stays green.
"""
