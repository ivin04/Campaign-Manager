from database import (
    execute,
    one,
    one_in_conn,
)


class CampaignRepository:

    def get_campaign(
        self,
        campaign_id: int = 1,
        *,
        conn=None,
    ):
        query = """
            SELECT *
            FROM campaign
            WHERE id=?
        """

        if conn is None:
            return one(
                query,
                (campaign_id,),
            )

        return one_in_conn(
            conn,
            query,
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
        *,
        conn=None,
    ):
        query = """
            SELECT *
            FROM sessions
            WHERE id=?
        """

        if conn is None:
            return one(
                query,
                (session_id,),
            )

        return one_in_conn(
            conn,
            query,
            (session_id,),
        )

    def get_current_session(
        self,
        campaign_id: int = 1,
        *,
        conn=None,
    ):
        campaign = self.get_campaign(
            campaign_id,
            conn=conn,
        )

        if campaign is None:
            return None

        session_id = campaign[
            "current_session_id"
        ]

        if session_id is None:
            return None

        return self.get_session(
            session_id,
            conn=conn,
        )

    def update_active_character(
        self,
        campaign_id: int,
        character_id: int | None,
    ):
        execute(
            """
            UPDATE campaign
            SET
                active_character_id=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                character_id,
                campaign_id,
            ),
        )

        return self.get_campaign(campaign_id)

    def get_active_character_id(
        self,
        campaign_id: int = 1,
        *,
        conn=None,
    ) -> int | None:
        campaign = self.get_campaign(
            campaign_id,
            conn=conn,
        )

        if campaign is None:
            return None

        return campaign[
            "active_character_id"
        ]