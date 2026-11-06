from test_game import clean, client, player, state


def test_state_contains_consolidated_web_projections(client):
    h = player(client)
    s = state(client, h)
    assert s["reward_records"] == client.get("/rewards", headers=h).json()
    assert s["guild_rewards"] == client.get("/guild/rewards", headers=h).json()
    assert s["fast_destinations"] == client.get("/fast-travel", headers=h).json()
    assert s["guild_treasury"].isdigit()


def test_logout_revokes_only_current_session_and_all_logout_revokes_the_rest(client):
    h = player(client)
    token = client.post(
        "/auth/login", json={"username": "alice", "password": "safe-pass-123"}
    ).json()["token"]
    other = {"Authorization": "Bearer " + token}
    assert client.post("/auth/logout", headers=h, json={}).status_code == 200
    assert client.get("/state", headers=h).status_code == 401
    assert client.get("/state", headers=other).status_code == 200
    assert client.post("/auth/logout-all", headers=other, json={}).status_code == 200
    assert client.get("/state", headers=other).status_code == 401
