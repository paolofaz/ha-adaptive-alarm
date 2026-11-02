"""Pure human-readable descriptions for UI and alarm notifications.

State lookup is supplied by the HA adapter. The pure engine still uses and
persists stable entity IDs; friendly names are presentation-only.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

NameOf = Callable[[str], str]


def group_summary(
    groups: Iterable[object], name_of: NameOf, *, alternative_word: str = "oppure",
) -> str:
    """Summarize every mandatory OR group without changing its logic."""
    rendered = []
    for group in groups:
        contacts = " " + alternative_word + " "
        rendered.append(
            f"{group.name}: " + contacts.join(name_of(c) for c in group.contacts)
        )
    return "; ".join(rendered) if rendered else "—"


def prealert_text(source: str, contact: str, name_of: NameOf) -> str:
    return (
        f"PREALLARME: vibrazione rilevata su {name_of(contact)} "
        f"(sensore: {name_of(source)}). Allarme non ancora scattato."
    )


def trigger_text(
    cause: str, links: Mapping[str, str], name_of: NameOf,
) -> str:
    """Explain precisely which protected contact or vibration caused trigger."""
    if cause.startswith("vibration:"):
        source = cause.removeprefix("vibration:")
        contact = links.get(source)
        if contact:
            detail = (
                f"vibrazioni ripetute su {name_of(contact)} "
                f"(sensore: {name_of(source)})"
            )
        else:
            detail = f"vibrazioni ripetute dal sensore {name_of(source)}"
    elif cause == "manual_test":
        detail = "attivazione manuale di prova"
    elif cause.startswith("binary_sensor."):
        detail = f"apertura del contatto {name_of(cause)}"
    else:
        detail = f"causa: {cause}"
    return f"ALLARME SIMULATO: {detail}. Sirena fisica NON attivata."


def fault_text(zone: str, state: str, name_of: NameOf) -> str:
    """Explain a protected contact fault without pretending it triggered."""
    if state == "unavailable":
        issue = "sensore non disponibile"
    elif state == "open":
        issue = "sensore tornato online già aperto"
    else:
        issue = "stato anomalo del sensore"
    return (
        f"AVVISO SENSORI: {name_of(zone)} — {issue}. "
        "Nessun allarme scattato automaticamente."
    )


def armed_text(protected: Iterable[str], excluded: Iterable[str], pending: Iterable[str]) -> str:
    """Describe only confirmed, committed arming, never the countdown."""
    return (
        "ALLARME INSERITO: protezione attiva. "
        f"{len(tuple(protected))} contatti protetti, "
        f"{len(tuple(excluded))} esclusi, {len(tuple(pending))} in attesa."
    )


def arm_rejected_text(
    problems: Iterable[str], paths: object, name_of: NameOf,
) -> str:
    """Render minimum coverage failures with friendly names and group members."""
    details: list[str] = []
    for problem in problems:
        if problem.startswith("mandatory_contact_not_closed:"):
            entity = problem.split(":", 1)[1]
            details.append(f"{name_of(entity)} non è chiuso o non è disponibile")
        elif problem.startswith("alternative_group_not_covered:"):
            group_name = problem.split(":", 1)[1]
            groups = getattr(paths, "groups", ())
            group = next((g for g in groups if g.name == group_name), None)
            if group is not None:
                alternatives = " oppure ".join(name_of(c) for c in group.contacts)
                details.append(
                    f"gruppo {group_name} non soddisfatto: "
                    f"nessuno tra {alternatives} risulta chiuso"
                )
            else:
                details.append(f"gruppo {group_name} non soddisfatto")
        elif problem == "lock_not_locked_or_unavailable":
            lock = getattr(paths, "lock", None)
            details.append(
                f"{name_of(lock)} non risulta bloccata"
                if lock else "serratura non bloccata o non disponibile"
            )
        elif problem == "protection_not_configured":
            details.append("nessun requisito di protezione configurato")
        elif problem == "entry_not_closed_or_unavailable":
            details.append("contatto di ingresso non chiuso o non disponibile")
        elif problem == "no_minimum_path":
            details.append("nessun percorso minimo di protezione soddisfatto")
        else:
            details.append(f"requisito non soddisfatto ({problem})")
    return (
        "INSERIMENTO RIFIUTATO: " + "; ".join(details or ["requisiti non soddisfatti"])
        + ". L'allarme rimane disinserito."
    )
