# Fix: "The string did not match the expected pattern" Error

## Problem
The chatbot was returning: `Error: The string did not match the expected pattern.`

This is a **Pydantic validation error** occurring when trying to create `AnswerResponse` or `SourceCitation` objects with invalid string values.

## Root Cause
Pydantic v2 has stricter validation rules. The error occurs when:
1. **Control characters** (like null bytes `\x00`) are present in strings
2. **Empty strings** are passed where non-empty strings are required
3. **Invalid characters** that don't match Pydantic's string pattern validation
4. **Special characters** in filenames, types, or content that Pydantic rejects

## Solution Implemented

### 1. Added String Sanitization Function
Created `sanitize_string()` helper function that:
- Removes null bytes and control characters
- Ensures non-empty strings with defaults
- Truncates strings to reasonable lengths
- Keeps only printable characters and common whitespace

### 2. Updated SourceCitation Creation
Now sanitizes all fields before creating `SourceCitation`:
- **filename**: Sanitized, max 255 chars, defaults to 'document'
- **type**: Sanitized, max 50 chars, defaults to 'document'  
- **content**: Sanitized, max 500 chars, defaults to 'No content available'
- **score**: Validated as float, defaults to 1.0 if invalid

### 3. Updated AnswerResponse Creation
- Sanitizes the answer string (max 10,000 chars)
- Validates all sources before including them
- Has fallback error handling if validation fails

## Code Changes

### New Function:
```python
def sanitize_string(value: str, default: str = '', max_length: int = None) -> str:
    """Sanitize string for Pydantic validation - remove control characters."""
    # Removes null bytes, control characters
    # Keeps only printable characters and whitespace
    # Returns default if empty
```

### Updated SourceCitation Creation:
```python
# Before: Direct assignment (could fail validation)
sources.append(SourceCitation(
    filename=safe_filename,
    type=safe_type,
    content=safe_content,
    score=score_value
))

# After: Sanitized fields with error handling
safe_filename = sanitize_string(filename, default='document', max_length=255)
safe_type = sanitize_string(doc_type, default='document', max_length=50)
safe_content = sanitize_string(content_preview, default='No content available', max_length=500)
# ... with try/except fallback
```

### Updated AnswerResponse Creation:
```python
# Before: Direct return (could fail validation)
return AnswerResponse(answer=safe_answer, sources=sources)

# After: Sanitized with error handling
safe_answer = sanitize_string(answer, default="I couldn't generate a response...", max_length=10000)
# ... with try/except fallback
```

## Testing

After deploying, test with:
1. Simple queries: "niche", "wall art vision exercise"
2. Complex queries: "should I focus on a niche?"
3. Edge cases: Queries that might return empty or malformed responses

## Expected Behavior

✅ **Before Fix**: Error "The string did not match the expected pattern"
✅ **After Fix**: Valid responses with properly sanitized fields

## Files Changed

- `serve.py`: Added `sanitize_string()` function and updated validation logic

## Next Steps

1. **Review the changes** in `serve.py`
2. **Deploy to Render** (after approval)
3. **Test the chatbot** with various queries
4. **Monitor logs** for any remaining validation errors

## If Error Persists

If you still see pattern validation errors:

1. **Check logs** for which field is failing:
   ```bash
   # Look for: "Failed to create SourceCitation" or "Failed to create AnswerResponse"
   ```

2. **Check for specific characters**:
   - Null bytes (`\x00`)
   - Control characters (ASCII 0-31 except \n, \t, \r)
   - Invalid Unicode characters

3. **Add more logging**:
   ```python
   logger.debug(f"Filename: {repr(filename)}")
   logger.debug(f"Type: {repr(doc_type)}")
   logger.debug(f"Content preview: {repr(content_preview[:100])}")
   ```

4. **Check Pydantic version**:
   ```bash
   pip show pydantic
   # Should be >= 2.0.0
   ```

