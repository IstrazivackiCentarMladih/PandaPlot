# High #7 — Analysis Engine Crashes on Single-Point Input

**Severity:** High  
**File:** `pandaplot/analysis/analysis_engine.py`  
**Lines:** 53–58

---

## Problem

`calculate_derivative()` handles forward and backward derivative methods by calling `np.diff()`, then padding the result to restore the original length:

```python
# analysis_engine.py:53-58
elif method == DerivativeMethod.FORWARD.value:
    derivative = np.diff(y_slice) / np.diff(x_slice)
    derivative = np.append(derivative, derivative[-1])  # Pad last value

else:  # backward
    derivative = np.diff(y_slice) / np.diff(x_slice)
    derivative = np.insert(derivative, 0, derivative[0])  # Pad first value
```

`np.diff()` on an array of length `n` returns an array of length `n-1`. For `n=1` (single data point), `np.diff()` returns an **empty array** (length 0).

Accessing `derivative[-1]` on an empty numpy array raises:

```
IndexError: index -1 is out of bounds for axis 0 with size 0
```

The same crash occurs for `derivative[0]` in the backward case.

This affects any user who:
- Selects a single-row dataset for derivative analysis.
- Specifies a start/end range that collapses to one point (e.g., `start_index=5, end_index=6`).

The central difference method (`np.gradient`) handles single-point input safely (it returns `[0.0]`), but the forward and backward methods do not.

Additionally, `calculate_arc_length()` has a milder version of the same pattern: `np.diff()` on a single-point slice returns an empty array, and `np.mean(arc_segments)` / `np.max(arc_segments)` are guarded with `if len(arc_segments) > 0`, but the `cumulative_length` result has length 1 while `arc_segments` has length 0 — this is consistent (the `np.insert(cumulative_length, 0, 0)` pad makes it length 1), so arc length doesn't crash, but the guard pattern should be applied consistently.

---

## Impact

- Unhandled `IndexError` propagates up through the call stack.
- Depending on how the analysis command handles exceptions, this either crashes the thread silently or shows a generic error dialog with no actionable message.
- Users with single-point datasets or narrow range selections get no useful feedback.

---

## Fix

Add a minimum-length guard at the top of `calculate_derivative()`, before the method dispatch:

```python
@staticmethod
def calculate_derivative(
    x_data: pd.Series,
    y_data: pd.Series,
    method: str = "central",
    start_index: int = 0,
    end_index: int = -1
) -> AnalysisResult:
    if end_index == -1:
        end_index = len(x_data)

    x_slice = x_data.iloc[start_index:end_index]
    y_slice = y_data.iloc[start_index:end_index]

    if len(x_slice) < 2:
        raise ValueError(
            f"Derivative requires at least 2 data points; got {len(x_slice)}. "
            f"Check your start/end index range."
        )

    # ... rest of calculation unchanged
```

For the forward/backward cases specifically, also add the pad-safety guard:

```python
elif method == DerivativeMethod.FORWARD.value:
    diff_y = np.diff(y_slice)
    diff_x = np.diff(x_slice)
    derivative = diff_y / diff_x
    # Safe pad: len(derivative) >= 1 because len >= 2 is guaranteed above
    derivative = np.append(derivative, derivative[-1])

else:  # backward
    diff_y = np.diff(y_slice)
    diff_x = np.diff(x_slice)
    derivative = diff_y / diff_x
    derivative = np.insert(derivative, 0, derivative[0])
```

The `ValueError` should be caught in the calling command and displayed to the user via `UIController.show_error()`.

---

## Additional: Division by zero when x values are identical

`np.diff(x_slice)` can return zeros if x values are repeated, causing `derivative = diff_y / diff_x` to produce `inf` or `nan`. This should also be guarded:

```python
diff_x = np.diff(x_slice)
if np.any(diff_x == 0):
    raise ValueError(
        "Derivative cannot be computed: duplicate x values detected. "
        "Ensure x data is strictly monotonically increasing."
    )
```

---

## Notes

- The central difference method (`np.gradient`) handles edge cases more robustly because NumPy implements it internally. Consider making `central` the only supported method unless forward/backward are explicitly needed, to reduce the surface area for edge-case bugs.
- Add unit tests for each method with: single-point input, two-point input, identical x values, and NaN values in y.
