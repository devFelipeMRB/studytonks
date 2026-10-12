# Formato JSON e regras de domínio

`state.json` é UTF-8, com `schema_version: 1`. A gravação usa arquivo temporário no mesmo diretório, `fsync`, seguido de `os.replace`; o snapshot anterior também é gravado atomicamente antes da troca. `QLockFile` impede escritores concorrentes em uma mesma pasta de dados. Backups ZIP também são escritos em arquivo temporário e substituídos atomicamente. Não são incluídas notas em logs.

Coleções de entidades possuem `id` UUID, `created_at` ISO local sem timezone e `updated_at` nas edições:

| Campo raiz | Conteúdo |
| --- | --- |
| `settings` | Tema, meta padrão, notificações, autostart, bandeja, horas, frequência/pasta de backups, período dos gráficos e checkpoint opcional `active_study` |
| `subjects` | `name`, `description`, `color`, `icon`, `target`, `archived` |
| `sessions` | `subject_id`, `title`; a posição na lista determina a ordem |
| `subsessions` | `subject_id`, `session_id`, `title`, `description`, `target`; posição na lista determina a ordem |
| `assessments` | `subject_id`, `session_id`/`subsession_id` opcionais, `name`, `date`, `obtained`, `maximum`, `percentage`, `method`, `components`, duração/observações/dificuldades opcionais |
| `study_logs` | IDs vinculados, `seconds` efetivos, `start`, `end`, `date` |
| `notes` | Dicionário por UUID da subsessão: `{format: "html", text: "...", updated_at: "..."}` |
| `bootcamps` | `subject_id`, `name`, `start`, `end`, `days`, `hours`, `target`, `sessions`, `plan`, `final_assessment` |
| `reminders` | `title`, `when`, `recurrence`, `days`, `enabled`, vínculos opcionais e `last_fired` |

Avaliações ordenam por `date`, timestamp `created_at` e UUID como último desempate. Porcentagens não são arredondadas no armazenamento, apenas na exibição. Todas as notas ficam entre 0 e 100. Nota máxima e pesos devem ser positivos e finitos.

- `points`: `obtained / maximum * 100`.
- `total_points`: soma dos pontos dos componentes dividida pela soma dos máximos.
- `weighted_percentages`: soma de cada porcentagem vezes seu peso, dividida pela soma dos pesos. Cada componente usa máximo 100 na interface.

Um componente tem `subsession_id`, `obtained`, `maximum`, `percentage`, e opcionalmente `mode`/`weight`. A subsessão não pode se repetir dentro da prova. O histórico geral conta a entidade avaliação uma única vez; o individual deriva somente dos componentes explicitamente cadastrados ou de uma prova diretamente vinculada à subsessão. A média é a média aritmética das avaliações, sem contagem extra dos componentes; evolução é última nota menos penúltima em pontos percentuais.

Ao mover subsessões, os vínculos diretos de registros e provas são atualizados na mesma transação. Arquivamento não apaga histórico. Excluir matéria remove os dados vinculados mediante confirmação. Remover uma prova que era final de bootcamp limpa essa referência, sem inventar uma substituta.

O progresso do bootcamp considera logs da matéria, período, dias escolhidos e sessões vinculadas; sem sessões selecionadas, considera todas. Aprovação requer escolher uma avaliação final dentro do período que atinja a meta; completar horas sozinho não aprova. Uma nova semana de reforço pode ser cadastrada após qualquer resultado.

A versão 0 de pré-lançamento é migrada para 1: preferências ausentes recebem padrões e notas em strings HTML recebem formato e timestamp. O original fica em `state.pre-migration.json`. Versões desconhecidas e snapshots estruturalmente inválidos são rejeitados; não há tentativa de inferir conteúdo perdido.

O checkpoint `settings.active_study` contém `link` (IDs vinculados), `seconds` e `start`. É retomado pausado; não utiliza diferença do relógio para contar tempo enquanto o programa estava fechado. Finalizar adiciona um log e limpa o checkpoint na mesma transação, evitando duplicações após reabertura.
