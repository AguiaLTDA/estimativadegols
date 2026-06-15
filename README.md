# Previsão de Gols - Base de Dados Preditiva da Copa do Mundo 2026

Este repositório contém a infraestrutura para construir uma base de dados preditiva focada nas 48 seleções que disputam a Copa do Mundo FIFA 2026. A base consolida os últimos 20 jogos oficiais e amistosos de cada equipe com pesos temporais e ajustes pela força do adversário (Elo e Ranking FIFA).

## 📊 Estrutura do Projeto

*   **`data_pipeline.py`**: Script Python principal que executa o download de dados, calcula o ELO histórico desde 1872 e processa as estatísticas ponderadas das seleções.
*   **`validate_data.py`**: Script de validação para garantir a integridade dos dados, tipos de variáveis e bounds matemáticos.
*   **`world_cup_2026_teams.json`**: Registro consolidado das 48 equipes em formato JSON.
*   **`world_cup_2026.db`**: Banco de dados SQLite contendo duas tabelas:
    *   `teams_summary`: Resumo estatístico de cada seleção.
    *   `team_matches`: Detalhamento das 20 partidas históricas utilizadas de cada equipe.

## 🛠️ Metodologia Utilizada

1.  **Pesos Temporais**: Aplicação de decaimento linear nos últimos 20 jogos. O jogo mais recente tem peso `1.00`, enquanto o 20º mais antigo tem peso de `0.40`.
2.  **Elo Rating Dinâmico**: Calculado partida a partida desde 1872 usando a fórmula clássica do World Football Elo Ratings (incluindo multiplicadores de saldo de gols e peso K por relevância da competição).
3.  **Força Ofensiva e Defensiva**: Média de gols marcados e sofridos ponderados, ajustados de acordo com a força média (Elo) dos adversários enfrentados.
4.  **Índice de Forma Recente**: Medido de `0` a `100` com base na diferença entre o resultado real da partida e a expectativa de vitória (probabilidade) calculada antes do jogo.

## 🚀 Como Executar

### Pré-requisitos
Apenas Python 3 (sem bibliotecas externas necessárias).

### Executando o Pipeline
Para rodar a simulação e gerar/atualizar a base de dados:
```bash
python data_pipeline.py
```

Para validar a integridade dos arquivos gerados:
```bash
python validate_data.py
```

## 📈 Exemplo de Dados Consolidados (JSON)
```json
{
  "team": "Brazil",
  "fifa_rank": 6,
  "elo": 2062,
  "form_index": 47.9,
  "attack_strength": 2.4,
  "defense_strength": 0.91,
  "weighted_win_rate": 0.51,
  "weighted_draw_rate": 0.25,
  "weighted_loss_rate": 0.24,
  "opponent_strength": 1913
}
```
