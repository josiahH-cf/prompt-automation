# GUI Parity Specification

This document summarizes the expected feature set for the selector, collector, and review windows. It serves as a reference for contributors implementing new front ends or porting the interface.

## Selector

- **Search**: realtime filtering of templates.
- **Recursive toggle**: include nested folders in search results.
- **Shortcuts**: numeric and hotkey mappings for quick launch.
- **Multi-select**: open multiple templates in sequence.
- **Geometry persistence**: window size and position remembered.
- **Error dialogs**: inform users when templates fail to load.

## Collector

- **Variable widgets**: appropriate widgets for each placeholder type.
- **Overrides & exclusions**: override stored values or omit variables.
- **Preview**: live preview of the prompt as values change.
- **Shortcuts**: keyboard navigation between fields.
- **Geometry persistence**: remembers window size and position.
- **Error dialogs**: highlight validation failures or missing inputs.

## Review

- **Search**: find text within the rendered prompt.
- **Overrides & exclusions**: adjust or skip variables before finalizing.
- **Preview**: display final prompt with substitutions.
- **Shortcuts & multi-select**: copy sections or open related templates quickly.
- **Geometry persistence**: restore last window size and position.
- **Error dialogs**: report copy or rendering issues.

