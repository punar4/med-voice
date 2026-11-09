"""Insert one synthetic profile with three medicines (T2).

Run from `backend/`:  ../venv/Scripts/python.exe seed.py

Two medicines are confirmed and one is deliberately left unconfirmed, so the
elder-side rules built in T4 have data that respects the "confirmed only" rule.
Everything here is invented for testing: no real people, phone numbers or
prescriptions. Re-running does nothing if the seed profile already exists.
"""

from datetime import date, timedelta

from sqlmodel import Session, select

from app import db
from app.models import Medicine, Profile

SEED_ELDER_NAME = "Synthetic Elder"
SEED_DAYS_AGO = 5


def main() -> None:
    db.init_db()

    with Session(db.engine) as session:
        existing = session.exec(
            select(Profile).where(Profile.elder_name == SEED_ELDER_NAME)
        ).first()
        if existing is not None:
            print(
                "Seed profile already exists: "
                f"id={existing.id} share_token={existing.share_token}"
            )
            return

        profile = Profile(elder_name=SEED_ELDER_NAME, language="kn")
        session.add(profile)
        session.commit()
        session.refresh(profile)

        start = date.today() - timedelta(days=SEED_DAYS_AGO)
        medicines = [
            Medicine(
                profile_id=profile.id,
                name="Amlodipine 5mg",
                aliases=["BP tablet", "amlo"],
                label="white round tablet",
                color_word="bili",
                dose="1 tablet",
                times=["morning"],
                food="after",
                days_total=30,
                start_date=start,
                purpose="BP",
                confirmed=True,
            ),
            Medicine(
                profile_id=profile.id,
                name="Metformin 500mg",
                aliases=["sugar tablet", "metfor"],
                label="big white tablet",
                color_word="bili",
                dose="1 tablet",
                times=["morning", "night"],
                food="after",
                days_total=60,
                start_date=start,
                purpose=None,  # nothing written on the prescription -> referral path
                confirmed=True,
            ),
            Medicine(
                profile_id=profile.id,
                name="Paracetamol 650mg",
                aliases=["fever tablet"],
                label="long white tablet",
                color_word="bili",
                dose="1 tablet",
                times=["night"],
                food="any",
                confirmed=False,  # the elder side must never see this one
            ),
        ]
        session.add_all(medicines)
        session.commit()

        print(f"Seeded profile id={profile.id}")
        print(f"  share_token={profile.share_token}")
        print(f"  elder link: /elder/{profile.share_token}")
        print(f"  medicines: {len(medicines)} (2 confirmed, 1 unconfirmed)")


if __name__ == "__main__":
    main()
