# Retained world-audit syntax failure

The first strict comparison script had one unmatched tuple parenthesis and stopped
at Python parsing (`SyntaxError: '(' was never closed`). No comparison executed,
no world-verification JSON was written and no screenshot was changed. Preserve the
script and traceback under `*-syntax-rejected.*`; the corrected script/log are
separate from those failures. This was an audit-script failure, not an observed
RGBA mismatch. Original captures remain unchanged and still require strict review.
