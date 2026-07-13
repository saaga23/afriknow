import modal

# Cheap auth + connectivity check (no GPU, no cost)
try:
    cfg = modal.config._lookup_workspace()
    print("workspace lookup OK:", cfg)
except Exception as e:
    print("workspace lookup via config failed:", repr(e))

# Alternative: a no-op app that just imports — proves token file is readable
try:
    app = modal.App.lookup("afriknow-annotator", create_if_missing=True)
    print("App lookup OK:", app.name)
except Exception as e:
    print("App lookup note:", repr(e))
print("MODAL_AUTH check complete (no GPU used)")
