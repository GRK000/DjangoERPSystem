def evidence_item(kind, label, url=None, metadata=None):
    data = {"type": kind, "label": str(label)}
    if url:
        data["url"] = url
    if metadata:
        data["metadata"] = metadata
    return data
