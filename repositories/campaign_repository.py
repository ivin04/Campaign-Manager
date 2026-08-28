from database import one, execute


class CampaignRepository:

    def get_campaign(self, campaign_id: int = 1):
        return one(
            """
            SELECT *
            FROM campaign
            WHERE id=?
            """,
            (campaign_id,),
        )

    def update_campaign(
        self,
        campaign_id: int,
        name: str,
        system: str,
        tone: str,
        summary: str,
    ):
        execute(
            """
            UPDATE campaign
            SET
                name=?,
                system=?,
                tone=?,
                summary=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                name,
                system,
                tone,
                summary,
                campaign_id,
            ),
        )

        return self.get_campaign(campaign_id)

    def update_current_session(
        self,
        campaign_id: int,
        session_id: int | None,
    ):
        execute(
            """
            UPDATE campaign
            SET
                current_session_id=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                session_id,
                campaign_id,
            ),
        )

        return self.get_campaign(campaign_id)

    def create_session(
        self,
        number: int,
        title: str,
        summary: str,
        start_location: str,
        end_location: str,
        notes: str,
    ):
        session_id = execute(
            """
            INSERT INTO sessions
                (
                    number,
                    title,
                    summary,
                    start_location,
                    end_location,
                    notes
                )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                number,
                title,
                summary,
                start_location,
                end_location,
                notes,
            ),
        )

        return one(
            """
            SELECT *
            FROM sessions
            WHERE id=?
            """,
            (session_id,),
        )

    def get_session(
        self,
        session_id: int,
    ):
        return one(
            """
            SELECT *
            FROM sessions
            WHERE id=?
            """,
            (session_id,),
        )

    def get_current_session(
        self,
        campaign_id: int = 1,
    ):
        campaign = self.get_campaign(campaign_id)

        if campaign is None:
            return None

        session_id = campaign["current_session_id"]

        if session_id is None:
            return None

        return self.get_session(session_id)