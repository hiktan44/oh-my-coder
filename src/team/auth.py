from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
takimkimlik dogrulamamodul

yonettakimolustur, oluyeyonetveizinkontrol. 
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from .task_sync import MemberRole


@dataclass
class TeamMember:
    """takimoluye"""

    user_id: str
    team_id: str
    role: MemberRole = MemberRole.MEMBER
    display_name: str = ""
    email: str = ""
    avatar_url: Optional[str] = None
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "team_id": self.team_id,
            "role": self.role.value,
            "display_name": self.display_name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "joined_at": self.joined_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "settings": self.settings,
        }


@dataclass
class Team:
    """takim"""

    team_id: str
    name: str
    owner_id: str
    description: str = ""
    invite_code: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    members: list[TeamMember] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "invite_code": self.invite_code,
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
            "member_count": len(self.members),
            "members": [m.to_dict() for m in self.members],
        }


@dataclass
class UserSession:
    """kullaniciyapacakkonusma"""

    session_id: str
    user_id: str
    team_id: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def is_valid(self) -> bool:
        return self.is_active and datetime.now() < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
        }


class TeamAuth:
    """
    takimkimlik dogrulamayonet

    Islev:
    - olustur/siltakim
    - eklegiris/geritakim
    - oluyeyonet
    - izindogrulama
    """

    def __init__(self):
        self._teams: dict[str, Team] = {}
        self._user_teams: dict[str, str] = {}  # user_id -> team_id
        self._sessions: dict[str, UserSession] = {}
        self._invite_codes: dict[str, str] = {}  # invite_code -> team_id

    def _generate_id(self) -> str:
        """olusturtekbir ID"""
        return secrets.token_hex(8)

    def _generate_invite_code(self) -> str:
        """olusturdavet kodu"""
        return secrets.token_urlsafe(6).upper()

    def _hash_password(self, password: str, salt: str) -> str:
        """hashgizlikod (PBKDF2-SHA256, 100k iterasyon) """
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100_000,
        ).hex()

    async def create_team(
        self,
        name: str,
        owner_id: str,
        description: str = "",
    ) -> Team:
        """
        olusturtakim

        Args:
            name: takimad
            owner_id: var ID
            description: takimaciklama

        Returns:
            Team: olusturtakim
        """
        team_id = f"team_{self._generate_id()}"
        invite_code = self._generate_invite_code()

        owner_member = TeamMember(
            user_id=owner_id,
            team_id=team_id,
            role=MemberRole.OWNER,
            joined_at=datetime.now(),
        )

        team = Team(
            team_id=team_id,
            name=name,
            owner_id=owner_id,
            description=description,
            invite_code=invite_code,
            members=[owner_member],
        )

        self._teams[team_id] = team
        self._user_teams[owner_id] = team_id
        self._invite_codes[invite_code] = team_id

        return team

    async def join_team(
        self,
        invite_code: str,
        user_id: str,
        display_name: str = "",
        email: str = "",
    ) -> Optional[Team]:
        """
        eklegiristakim

        Args:
            invite_code: davet kodu
            user_id: kullanici ID
            display_name: gosterad
            email: eposta

        Returns:
            Team: eklegiristakim
        """
        team_id = self._invite_codes.get(invite_code)
        if not team_id:
            return None

        team = self._teams.get(team_id)
        if not team:
            return None

        # kontrololup olmadigieklegiris
        if any(m.user_id == user_id for m in team.members):
            return team

        member = TeamMember(
            user_id=user_id,
            team_id=team_id,
            role=MemberRole.MEMBER,
            display_name=display_name,
            email=email,
            joined_at=datetime.now(),
        )

        team.members.append(member)
        self._user_teams[user_id] = team_id

        return team

    async def leave_team(self, user_id: str, team_id: str) -> bool:
        """
        ayrilactakim

        Args:
            user_id: kullanici ID
            team_id: takim ID

        Returns:
            bool: basarili mi
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # varhayiredebilirayrilac
        if team.owner_id == user_id:
            return False

        team.members = [m for m in team.members if m.user_id != user_id]
        self._user_teams.pop(user_id, None)

        return True

    async def delete_team(self, team_id: str, requester_id: str) -> bool:
        """
        siltakim

        Args:
            team_id: takim ID
            requester_id: istek ID

        Returns:
            bool: basarili mi
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # sadecevarvarolabilirilesil
        if team.owner_id != requester_id:
            return False

        # temizlekullaniciiliskili
        for member in team.members:
            self._user_teams.pop(member.user_id, None)

        # temizledavet kodu
        self._invite_codes.pop(team.invite_code, None)

        del self._teams[team_id]

        return True

    async def get_team(self, team_id: str) -> Optional[Team]:
        """altakim"""
        return self._teams.get(team_id)

    async def get_user_team(self, user_id: str) -> Optional[Team]:
        """alkullaniciicindetakim"""
        team_id = self._user_teams.get(user_id)
        if team_id:
            return self._teams.get(team_id)
        return None

    async def update_member_role(
        self,
        team_id: str,
        user_id: str,
        new_role: MemberRole,
        requester_id: str,
    ) -> bool:
        """
        guncelleoluyerol

        Args:
            team_id: takim ID
            user_id: hedefisaretkullanici ID
            new_role: yenirol
            requester_id: istek ID

        Returns:
            bool: basarili mi
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # sadecevarvarolabiliriledahadegistirrol
        if team.owner_id != requester_id:
            return False

        for member in team.members:
            if member.user_id == user_id:
                member.role = new_role
                return True

        return False

    def check_permission(
        self,
        user_id: str,
        team_id: str,
        required_role: MemberRole,
    ) -> bool:
        """
        kontrolizin

        Args:
            user_id: kullanici ID
            team_id: takim ID
            required_role: gerekisterrol

        Returns:
            bool: olup olmadigivarizin
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        for member in team.members:
            if member.user_id == user_id:
                role_order = {
                    MemberRole.OWNER: 3,
                    MemberRole.ADMIN: 2,
                    MemberRole.MEMBER: 1,
                }
                return role_order.get(member.role, 0) >= role_order.get(
                    required_role, 0
                )

        return False

    async def create_session(
        self,
        user_id: str,
        team_id: str,
        expires_in_hours: int = 24,
    ) -> UserSession:
        """
        olusturyapacakkonusma

        Args:
            user_id: kullanici ID
            team_id: takim ID
            expires_in_hours: donemzamanarasinda (kucukzaman) 

        Returns:
            UserSession: olusturyapacakkonusma
        """
        session_id = f"session_{self._generate_id()}"

        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            team_id=team_id,
            expires_at=datetime.now() + timedelta(hours=expires_in_hours),
        )

        self._sessions[session_id] = session
        return session

    async def validate_session(self, session_id: str) -> Optional[UserSession]:
        """dogrulamayapacakkonusma"""
        session = self._sessions.get(session_id)
        if session and session.is_valid():
            return session
        return None

    async def invalidate_session(self, session_id: str) -> bool:
        """izinyapacakkonusmakayipetki"""
        if session_id in self._sessions:
            self._sessions[session_id].is_active = False
            return True
        return False

    async def regenerate_invite_code(
        self, team_id: str, requester_id: str
    ) -> Optional[str]:
        """
        tekraryeniolusturdavet kodu

        Args:
            team_id: takim ID
            requester_id: istek ID

        Returns:
            str: yenidavet kodu
        """
        team = self._teams.get(team_id)
        if not team or team.owner_id != requester_id:
            return None

        # sileskidavet kodu
        self._invite_codes.pop(team.invite_code, None)

        # olusturyenidavet kodu
        team.invite_code = self._generate_invite_code()
        self._invite_codes[team.invite_code] = team_id

        return team.invite_code


# globalornek
team_auth = TeamAuth()
