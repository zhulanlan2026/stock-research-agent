from stock_research.iam.permissions import permissions_for_roles


def test_permissions_for_roles_merges_role_codes() -> None:
    codes = permissions_for_roles(["FREE_USER", "REVIEWER"])
    assert "research.quick.execute" in codes
    assert "report.review" in codes
    assert "admin.user.manage" not in codes


def test_admin_has_all_permissions() -> None:
    codes = permissions_for_roles(["ADMIN"])
    assert "admin.user.manage" in codes
    assert "research.deep.execute" in codes


def test_unknown_role_is_ignored() -> None:
    assert permissions_for_roles(["UNKNOWN"]) == frozenset()
