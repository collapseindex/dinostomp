"""A Jev-like scorer mounted as a dinostomp examinee.

One forward pass: the item's context and its option list go in, one
probability per option comes out, the argmax option's text is the answer.
Under `--probe blind` dinostomp replaces the context with an uninformative
stub and keeps the options, so the same pass answers from the menu alone;
R13 and R15 compare the two.

The checkpoint path is relative to this file. It is loaded once per process.
"""

from __future__ import annotations

import os

_MODEL = None
_COLLATOR = None
_DEVICE = None
CHECKPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wikispeedia.pt")


def _load():
    global _MODEL, _COLLATOR, _DEVICE
    if _MODEL is None:
        import torch
        from jevlike.model import load_checkpoint, select_device

        _DEVICE = select_device("cpu")
        _MODEL, _COLLATOR, _ = load_checkpoint(CHECKPOINT, _DEVICE)
        _MODEL.eval()
        torch.set_num_threads(max(1, os.cpu_count() // 2))
    return _MODEL, _COLLATOR, _DEVICE


def run(item: dict, ctx: dict) -> dict:
    import torch
    from jevlike.data import ChoiceExample
    from jevlike.train import move

    model, collator, device = _load()
    options = [str(c) for c in item["choices"]]
    batch = move(collator([ChoiceExample(str(item["input"]), tuple(options), 0)]), device)
    with torch.no_grad():
        probabilities = model(batch).softmax(-1)[0, :len(options)].cpu().tolist()
    best = max(range(len(options)), key=lambda i: probabilities[i])
    # The probability vector rides along as evidence. dinostomp records it
    # verbatim and asserts nothing about it; the answer is the option text.
    return {
        "output": options[best],
        "trajectory": [{"tool": "score_options", "args": {"n_options": len(options)},
                        "result": {"top": options[best], "p_top": round(probabilities[best], 4),
                                   "p_target": round(probabilities[options.index(item["target"])], 4)
                                   if item.get("target") in options else None},
                        "ok": True}],
    }
