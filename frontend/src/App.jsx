import { useEffect, useState } from "react";
import api from "./api";
import { LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";

function App() {
  const [teams, setTeams] = useState([]);
  const [teamDetail, setTeamDetail] = useState(null);
  const [history, setHistory] = useState([]);

  const [newTeamName, setNewTeamName] = useState("");
  const [ownerName, setOwnerName] = useState("");

  const [newPlayerId, setNewPlayerId] = useState("");
  const [newPlayerName, setNewPlayerName] = useState("");

  const [warTable, setWarTable] = useState(null);
  const [summary, setSummary] = useState([]);

const [editPlayerId, setEditPlayerId] = useState("");
const [newPlayerIdValue, setNewPlayerIdValue] = useState("");

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    const res = await api.get("/teams");
    setTeams(res.data);
  };

  const selectTeam = async (team) => {
    const detail = await api.get(`/teams/${team.id}`);
    setTeamDetail(detail.data);

    const hist = await api.get(`/teams/${team.id}/war-history`);
    setHistory(hist.data);

    const table = await api.get(`/teams/${team.id}/war-table`);
    setWarTable(table.data);
  };

  const createTeam = async () => {
    if (!newTeamName) return;

    await api.post(`/teams`, null, {
      params: { name: newTeamName, owner_name: ownerName }
    });

    setNewTeamName("");
    setOwnerName("");
    fetchTeams();
  };

  const addPlayer = async () => {
    if (!teamDetail) return;

    await api.post(`/teams/${teamDetail.team_id}/players`, null, {
      params: {
        player_id: Number(newPlayerId),
        name: newPlayerName
      }
    });

    const detail = await api.get(`/teams/${teamDetail.team_id}`);
    setTeamDetail(detail.data);

    setNewPlayerId("");
    setNewPlayerName("");
  };

  const removePlayer = async (playerId) => {
    await api.delete(`/teams/${teamDetail.team_id}/players/${playerId}`);

    const detail = await api.get(`/teams/${teamDetail.team_id}`);
    setTeamDetail(detail.data);
  };

  const fetchWar = async () => {
    await api.post("/fetch-war");

    const detail = await api.get(`/teams/${teamDetail.team_id}`);
    setTeamDetail(detail.data);

    const hist = await api.get(`/teams/${teamDetail.team_id}/war-history`);
    setHistory(hist.data);

    const table = await api.get(`/teams/${teamDetail.team_id}/war-table`);
    setWarTable(table.data);
  };

const updatePlayerId = async () => {
  await api.put(
    `/teams/${teamDetail.team_id}/players/${editPlayerId}`,
    null,
    {
      params: {
        new_player_id: Number(newPlayerIdValue)
      }
    }
  );

  const detail = await api.get(`/teams/${teamDetail.team_id}`);
  setTeamDetail(detail.data);

  setEditPlayerId("");
  setNewPlayerIdValue("");
};

const fetchWarPit = async () => {
  await api.post("/fetch-war-pit");

  const detail = await api.get(`/teams/${teamDetail.team_id}`);
  setTeamDetail(detail.data);

  const hist = await api.get(`/teams/${teamDetail.team_id}/war-history`);
  setHistory(hist.data);
};

  const fetchSummary = async () => {
    const res = await api.get("/teams-summary");
    setSummary(res.data);
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>MLB WAR Tracker</h1>

      {/* チーム作成 */}
      <h2>Create Team</h2>
      <input value={newTeamName} onChange={(e) => setNewTeamName(e.target.value)} placeholder="Team name" />
      <input value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="Owner name" />
      <button onClick={createTeam}>Create</button>

      {/* チーム一覧 */}
      <h2>Teams</h2>
      {teams.map(t => (
        <button key={t.id} onClick={() => selectTeam(t)}>
          {t.name}
        </button>
      ))}

      <button onClick={fetchSummary} style={{ marginLeft: 10 }}>
        全チーム一覧
      </button>

      {/* チーム詳細 */}
      {teamDetail && (
        <>
          <h2>{teamDetail.team_name}</h2>

          <h3>Add Player</h3>
          <input value={newPlayerId} onChange={(e) => setNewPlayerId(e.target.value)} placeholder="Player ID" />
          <input value={newPlayerName} onChange={(e) => setNewPlayerName(e.target.value)} placeholder="Player Name" />
          <button onClick={addPlayer}>Add</button>

          <button onClick={fetchWar}>
  Fetch WAR (BAT)
</button>

<button onClick={fetchWarPit} style={{ marginLeft: 10 }}>
  Fetch WAR (PIT)
</button>

<h3>Fix Player ID</h3>

<input
  placeholder="Current ID"
  value={editPlayerId}
  onChange={(e) => setEditPlayerId(e.target.value)}
/>

<input
  placeholder="New ID"
  value={newPlayerIdValue}
  onChange={(e) => setNewPlayerIdValue(e.target.value)}
/>

<button onClick={updatePlayerId}>
  Update ID
</button>

          <h3>Players</h3>
          <ul>
            {teamDetail.players.map(p => (
              <li key={p.player_id}>
                {p.name} - WAR: {p.fwar ?? "N/A"}
                <button onClick={() => removePlayer(p.player_id)} style={{ marginLeft: 10 }}>
                  ❌
                </button>
              </li>
            ))}
          </ul>

          {/* WARテーブル */}
          {warTable && (
            <>
              <h3>WAR Table</h3>
              <table border="1">
                <thead>
                  <tr>
                    <th>Player ID</th>
                    <th>Player</th>
                    {warTable.dates.map(d => (
                      <th key={d}>{d}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {warTable.players.map(p => (
                    <tr key={p.player_id}>
                      <td>{p.player_id}</td>
                      <td>{p.name}</td>
                      {p.wars.map((w, i) => (
                        <td key={i}>{w ?? "DNP"}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h3>WAR Graph</h3>
          <LineChart width={500} height={300} data={history}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="total_war" />
          </LineChart>
        </>
      )}

      {/* 全チーム一覧 */}
      {summary.map((team, i) => (
        <div key={i}>
          <h3>{team.team_name} (Total: {team.total_war.toFixed(1)})</h3>
          <ul>
            {team.players.map((p, j) => (
              <li key={j}>
                {p.name}: {p.war}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default App;