"""Pinned W02 user-facing response selection, reused without content grading."""

class ReviewError(ValueError):
    pass

def object_list(value):
    return (item for item in (value or []) if isinstance(item, dict))

def response_for_review(raw):
    """Select user-facing text and literal citation fields. Never execute the response."""
    text, links = [], []
    safety_signal = False

    def add(value):
        if isinstance(value, str) and value:
            text.append(value)

    def cite(value, title=None):
        if isinstance(value, str) and value:
            links.append({"url": value, "title": title if isinstance(title, str) else ""})

    if "output" in raw:
        for item in object_list(raw["output"]):
            if item.get("type") != "message":
                continue
            for part in object_list(item.get("content")):
                if part.get("type") == "output_text":
                    add(part.get("text"))
                    for annotation in object_list(part.get("annotations")):
                        cite(annotation.get("url"), annotation.get("title"))
                elif part.get("type") == "refusal":
                    add(part.get("refusal"))
                    safety_signal = True
    elif "content" in raw:
        for part in object_list(raw["content"]):
            if part.get("type") == "text":
                add(part.get("text"))
                for citation in object_list(part.get("citations")):
                    cite(citation.get("url"), citation.get("title") or citation.get("document_title"))
        safety_signal = raw.get("stop_reason") == "refusal"
    elif "candidates" in raw or "promptFeedback" in raw:
        feedback = raw.get("promptFeedback") or {}
        safety_signal = bool(feedback.get("blockReason"))
        for candidate in object_list(raw.get("candidates")):
            for part in object_list((candidate.get("content") or {}).get("parts")):
                if not part.get("thought"):
                    add(part.get("text"))
            safety_signal |= candidate.get("finishReason") in {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
            grounding = candidate.get("groundingMetadata") or {}
            for chunk in object_list(grounding.get("groundingChunks")):
                web = chunk.get("web") or {}
                cite(web.get("uri"), web.get("title"))
            for source in object_list((candidate.get("citationMetadata") or {}).get("citationSources")):
                cite(source.get("uri"))
    elif "choices" in raw:
        for choice in object_list(raw["choices"]):
            message = choice.get("message") or {}
            add(message.get("content"))
            add(message.get("refusal"))
            safety_signal |= bool(message.get("refusal")) or choice.get("finish_reason") == "content_filter"
    else:
        raise ReviewError("Unsupported response envelope")

    for value in raw.get("citations") or []:
        cite(value)
    unique_links = list({(item["url"], item["title"]): item for item in links}.values())
    return "\n".join(text), unique_links, safety_signal
