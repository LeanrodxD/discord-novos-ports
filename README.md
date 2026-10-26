# Monitor de Ports PC → Discord

Bot gratuito que roda no GitHub Actions e avisa no Discord:

- 🆕 **Projetos novos** de ports nativos para PC (decompilações e recompilações de jogos de Switch, PS2, Xbox, Xbox 360, N64, GameCube/Wii, PS1, PSP, 3DS/DS e Dreamcast).
- 🔄 **Atualizações** (novas releases) dos projetos acompanhados.

Cada aviso traz, no campo **📀 ROM/ISO necessária**, o jogo exigido pelo projeto e o link do README oficial com as instruções para extrair o *seu próprio* dump. **Este projeto não distribui nem indica links de download de ROMs/ISOs.**

---

## Como funciona

1. A cada 3 horas, o workflow executa `monitor.py`.
2. **Descoberta:** busca na API do GitHub repositórios criados nos últimos dias que combinem com termos como `decompilation`, `recompilation`, `pc port` e `native port`, com mínimo de stars e alguma plataforma citada.
3. **Atualizações:** consulta a última release de cada projeto da `watchlist.json` e dos projetos descobertos.
4. Envia os avisos para o Discord via webhook.
5. Salva o que já foi visto em `state.json` (commit automático) para não repetir avisos.

A **primeira execução é silenciosa**: só registra o estado, sem enviar nada.

## Estrutura

```
├── .github/workflows/monitor.yml   # agendamento e execução
├── monitor.py                      # lógica do bot
├── watchlist.json                  # projetos acompanhados
├── requirements.txt                # dependências (requests)
├── state.json                      # criado automaticamente
└── README.md
```

## Configuração inicial

1. **Webhook do Discord:** canal → Editar canal → Integrações → Webhooks → Novo webhook → Copiar URL.
2. **Repositório público no GitHub** com todos os arquivos acima (o `monitor.yml` precisa ficar em `.github/workflows/`).
3. **Segredos:** Settings → Secrets and variables → Actions → New repository secret.
   - `DISCORD_WEBHOOK`: webhook dos avisos de projetos novos (e de tudo, se não houver o segundo).
   - `DISCORD_WEBHOOK_UPDATES` *(opcional)*: webhook de outro canal só para atualizações.
4. **Permissão de escrita:** Settings → Actions → General → Workflow permissions → **Read and write permissions**.
5. **Primeira execução:** Actions → Monitor de ports → Run workflow.

## Como atualizar e manter

### Adicionar um projeto para acompanhar
Edite `watchlist.json` e acrescente um item:

```json
{"repo": "dono/repositorio", "game": "Nome do jogo exigido"}
```

O formato simples `"dono/repositorio"` também funciona (o campo do jogo fica sem o nome). Projetos adicionados depois entram em silêncio: o bot só registra a release atual e avisa as próximas.

### Remover um projeto
Apague o item de `watchlist.json`. Se ele foi descoberto automaticamente, remova também o nome em `"tracked"` no `state.json`.

### Ajustar a descoberta
Variáveis no passo `env` do `monitor.yml` (opcionais):

| Variável | Padrão | Função |
|---|---|---|
| `MIN_STARS` | `10` | Mínimo de stars para um projeto novo ser avisado |
| `LOOKBACK_DAYS` | `7` | Idade máxima (dias) dos repositórios buscados |
| `REQUIRE_PLATFORM` | `1` | `0` aceita projetos sem plataforma identificada |
| `DRY_RUN` | `0` | `1` roda sem enviar nada ao Discord |

Para mudar as plataformas ou os termos de busca, edite `PLATFORMS` e `QUERIES` no início do `monitor.py`.

### Mudar a frequência
No `monitor.yml`, altere o `cron` (padrão `"0 */3 * * *"`, a cada 3 horas). Evite intervalos muito curtos.

### Reenviar tudo (forçar envio)
1. Em `state.json`, deixe `"seen": []` para reenviar também os projetos descobertos (não apague o arquivo).
2. Actions → Monitor de ports → Run workflow → marque **"Reenviar a última release de todos os projetos"** → Run.
3. Depois, nas execuções seguintes, volte a deixar a caixa desmarcada.

### Personalizar a aparência
- **Rodapé:** linhas `"footer"` em `discover` e `check_releases` no `monitor.py`. O Discord não permite alterar o tamanho da letra do rodapé; para texto maior, use títulos markdown (`##`) na descrição ou no `content` da mensagem.
- **Cores:** valores `"color"` dos embeds (verde = novo, azul = release, amarelo = pré-lançamento).

### Atualizar o código
Edite o arquivo direto no GitHub (lápis → Commit changes) ou via Git. A próxima execução já usa a versão nova.

## Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| Falha no passo `pip install` | `requirements.txt` ausente na raiz | Criar o arquivo com a linha `requests` |
| Falha no passo `Salvar estado` | Sem permissão de escrita | Ativar *Read and write permissions* |
| Nada chega ao Discord | Segredo com nome errado ou URL incompleta | Conferir `DISCORD_WEBHOOK` |
| Nada chega ao Discord, sem erros | Nada novo desde a última execução | Usar o modo forçar envio para testar |
| Caixa "Reenviar…" não aparece | `inputs` ausente no `monitor.yml` da branch `main` | Salvar o workflow completo e atualizar a página |
| Projeto não gera aviso | Ele não publica *Releases* no GitHub | Acompanhar via feed de commits em um leitor de RSS |
| Erro 403/429 na API | Limite de requisições | Aumentar o intervalo do `cron` |

## Limitações

- Só enxerga **Releases do GitHub** (não commits, builds de CI ou GitLab).
- A descoberta pode ter falsos positivos (ex.: "switch" no sentido de interruptor).
- Repositórios podem mudar de nome ou sair do ar; revise a `watchlist.json` de tempos em tempos.

## Aviso legal

Os projetos monitorados exigem que você forneça o jogo original que possui. Este bot não hospeda, distribui nem indica downloads de ROMs/ISOs.
