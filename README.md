# Studytonks

**Learn. Track. Master.** Aplicativo desktop offline para organizar um bootcamp pessoal de estudos, feito com Python 3.12, PySide6 e PyQtGraph. A instalação começa vazia: nenhum exemplo é inserido nos dados pessoais.

## Instalar no Windows — sem Python

O caminho para usar o aplicativo é baixar **Studytonks-Setup.exe** na [página de versões](https://github.com/devFelipeMRB/studytonks/releases), abrir o arquivo e seguir o instalador em português. Python, Qt, NumPy, PyQtGraph e os runtimes necessários já estão no pacote. A instalação e o uso funcionam offline após baixar o arquivo; o usuário final não precisa executar comandos ou instalar bibliotecas.

O instalador usa `%LOCALAPPDATA%\Programs\Studytonks`, sem administrador, cria um atalho no menu Iniciar e oferece atalho opcional na área de trabalho. Atualizar ou desinstalar preserva `%APPDATA%\Studytonks`. A opção de iniciar com Windows continua dependendo de autorização explícita nas Configurações.

[Mini site de download](https://devFelipeMRB.github.io/studytonks/) · [Projeto completo na branch de desenvolvimento](https://github.com/devFelipeMRB/studytonks/tree/development/studytonks-desktop) · [Código-fonte ZIP](https://github.com/devFelipeMRB/studytonks/archive/refs/heads/development/studytonks-desktop.zip)

O site e o instalador só ficam disponíveis após a publicação correspondente. O site mostra “Instalador em preparação” se a versão Windows ainda não tiver sido publicada. Não é gerado um executável Windows fictício no Linux.

## Iniciar em desenvolvimento

Windows 10/11, Python 3.12 estável instalado com o Python Launcher:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe main.py
```

Linux com uma sessão gráfica:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python main.py
```

Internet é necessária para instalar dependências; o aplicativo instalado não faz requisições de rede, não exige conta e funciona offline. No Linux sem display, use `QT_QPA_PLATFORM=offscreen` **somente para os testes**. Isso não oferece uma janela interativa.

## O que funciona

- Janela única com nove áreas, sidebar, temas claro/escuro/automático e escala DPI do Qt.
- Matérias com descrição, palavras-chave, cor, ícone, meta, edição, arquivamento e exclusão confirmada.
- Busca instantânea sem distinção de caixa ou acentos, palavras parciais e ordenação por nome, criação, atividade, nota e tendência.
- Árvore matéria → sessão → subsessão; renomear, mover subsessões entre sessões e alterar a ordem com ↑/↓.
- Editor com títulos, parágrafos, negrito, itálico, listas e fonte de código. Autosave após 600 ms sem digitação e ao navegar/fechar. Fórmulas LaTeX permanecem como texto legível.
- Avaliações por pontos ou porcentagem, data, duração, observações e dificuldades; edição preserva o ID, remoção pede confirmação.
- Provas com várias subsessões: total dos pontos ou porcentagens ponderadas com pesos positivos; método mostrado no formulário. A prova global conta uma vez, sem gerar notas para subsessões ausentes.
- Gráficos interativos com zoom/pan, tooltips, marcadores, meta e segmentos de progresso/regressão/estabilidade. Métricas com média, extremos e variação em pontos percentuais.
- Cronômetro em Estatísticas: iniciar, pausar, continuar, encerrar/salvar; tempo manual com data e vínculos; horas semanais e mensais, gráficos globais e ranking.
- Bootcamps em Detalhes da matéria: período, dias, sessões, plano por dia, metas, progresso e avaliação final explícita. A aprovação considera a nota final dentro do período. Novos bootcamps de reforço são permitidos.
- Lembretes únicos, diários ou em dias da semana, editar/desativar/excluir, vínculos com matéria/sessão e controle persistente contra duplicação.
- Preferências salvas imediatamente, backup automático/manual, exportação e restauração ZIP validada.

## Primeiro uso

1. Dashboard → **Nova matéria** → Matemática Computacional.
2. Sessões e submatérias → **Sessão** → Limites → **Subsessão** → Limites indeterminados.
3. Anotações → selecione a subsessão → escreva. O status indica quando foi salvo.
4. Estatísticas → **Iniciar** ou **Tempo manual** para registrar estudo.
5. Avaliações → **Registrar avaliação** → 18 pontos de 20 → resultado 90%.
6. Detalhes da matéria ou Anotações → acompanhe o gráfico geral ou individual.

## Dados e integridade

No Windows: **`%APPDATA%\Studytonks\`**. No Linux: `~/.local/share/Studytonks/`. `STUDYTONKS_DATA_DIR` permite escolher outra pasta, especialmente para testes. Dados nunca são gravados dentro do executável ou do diretório temporário do PyInstaller.

```text
Studytonks/
├── state.json                 # snapshot JSON transacional, esquema 1
├── state.previous.json        # snapshot válido anterior
├── state.pre-migration.json   # original, quando houver migração
├── corrupt-*.json             # originais corrompidos preservados
├── .writer.lock               # bloqueio de uma instância por pasta
├── backups/                   # ZIPs automáticos e manuais
└── logs/app.log               # erros por tipo, com rotação
```

Foi escolhida uma alternativa à divisão em muitos arquivos: um snapshot JSON permite atualizar referências relacionadas em **uma gravação atômica**, evitando índices e notas inconsistentes após falhas. Cada entidade tem UUID; nomes não viram caminhos. A cópia anterior e os backups permitem recuperação. O esquema valida tipos, referências, datas, notas e fórmulas de agregação antes de gravar/restaurar. Veja [formato dos dados](docs/data-format.md).

O autosave preserva conteúdo textual e formatação em HTML do Qt. Backup automático é verificado a cada gravação; a frequência é em dias, 0 desativa. Mantém os últimos 30 backups automáticos; manuais não são removidos. A pasta de backups pode ser alterada. Um ZIP exportado contém `state.json`, sem logs ou arquivos privados auxiliares. A restauração valida antes de substituir e cria um ZIP de segurança. Arquivos ZIP com entradas extras, caminhos inseguros, estrutura inválida ou tamanho descompactado acima de 50 MB são recusados. Nenhum ZIP é extraído diretamente no sistema de arquivos.

Se o principal estiver corrompido, a última cópia válida é recuperada e o original preservado. Se ambos estiverem inválidos, a inicialização oferece selecionar um backup válido; sem isso, não sobrescreve os arquivos existentes. Dados com versões futuras desconhecidas não são aceitos silenciosamente. Logs não incluem o texto das anotações.

## Notificações, bandeja e inicialização

O Qt usa a bandeja e as notificações nativas disponíveis no Windows. Clicar na notificação abre o aplicativo quando o sistema oferece esse evento; o Qt não fornece IDs confiáveis de cada notificação para escolher uma matéria específica. O menu permite abrir, iniciar estudo, acessar configurações ou sair completamente. **Lembretes exigem o processo em execução**, inclusive oculto na bandeja; o programa totalmente fechado não notifica. Focus Assist e preferências do Windows podem impedir a exibição, sem garantia de recibo de entrega.

A agenda compara o horário local do computador, persiste cada ocorrência antes de notificar e evita repetições. Após uma suspensão ou abertura muito tardia, ocorrências com mais de dois minutos são descartadas para evitar uma enxurrada de mensagens. Não há serviço ou tarefa externa que acorde o computador.

A opção de inicialização automática só atua após marcação e confirmação do usuário. Cria exclusivamente o valor **Studytonks** em `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, sem administrador; aponta para o executável atual (ou Python e `main.py` em desenvolvimento). Desativar remove apenas esse valor. Não há alterações no registro ao instalar, importar backup ou abrir o aplicativo. Se mover a distribuição para outra pasta, reconfigure essa opção. Sem bandeja disponível, ocultação e início minimizado ficam indisponíveis.

## Compilar o instalador para Windows

Ferramentas do **desenvolvedor**: Windows 10 versão 1809+/Windows 11, Python 3.12 de 64 bits com o Python Launcher e [Inno Setup 6.3 ou superior](https://jrsoftware.org/isinfo.php). O usuário final não precisa dessas ferramentas.

Execute `build.bat`. Ele instala os requisitos fixados, testa o aplicativo, gera a distribuição Qt com PyInstaller, verifica Python/Qt e os runtimes VC++ embarcados, abre o executável em teste isolado e compila o instalador Inno Setup:

```text
dist/release/
├── Studytonks-Setup.exe       # Instalar com dois cliques
├── Studytonks-Portable.zip    # Alternativa sem instalação
├── Studytonks-Source.zip      # Projeto completo
└── SHA256SUMS.txt             # Integridade dos downloads
```

Para gerar somente a alternativa portátil, use `build.bat --app-only`. Extraia o ZIP inteiro e abra `Studytonks/Studytonks.exe`; preserve a pasta `_internal`. O executável GUI não abre terminal. O empacotamento é one-folder, para maior confiabilidade com Qt, e o instalador reúne essa pasta em um único arquivo de download. Binários novos usam a pasta de dados existente.

O workflow `.github/workflows/windows.yml` executa os testes em um runner Windows, cria os binários, instala/atualiza a aplicação em uma pasta de teste, abre o Qt empacotado e desinstala verificando a preservação de dados. Tags `v*` precisam corresponder à versão do `pyproject.toml`; a release pública só é criada após os testes e upload de todos os arquivos. Para a versão atual, a tag é `v1.0.1`.

O workflow de site confirma os assets publicados antes de habilitar o download. Ele publica `site/` no GitHub Pages; se a configuração do repositório não permitir ativação automática, escolha **Settings → Pages → Source: GitHub Actions**. Nenhum valor pessoal ou credencial vai para os arquivos do site.

O instalador não possui assinatura Authenticode. O Windows pode mostrar “editor desconhecido”; consulte o FAQ do site e os checksums. PyInstaller/Inno precisam executar em Windows: a geração Linux serve para validar o empacotamento Linux e não gera `.exe` Windows.

## Testar

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/smoke.py
.venv/bin/ruff check --select F app tests tools main.py
```

No Windows, use `.venv\Scripts\python.exe -m pytest -q`; o fixture usa Qt offscreen. Os testes usam pastas temporárias e não alteram os dados pessoais. `tools/smoke.py` abre de verdade todas as páginas Qt com registros exclusivamente temporários, depois fecha e descarta a pasta. A validação atual passou **68 testes** no Linux offscreen, e o binário Linux gerado pelo PyInstaller executou `--smoke-test` com sucesso. Isso não valida o executável Windows. Os testes cobrem persistência após reabertura, cálculos, avaliações compostas, cronômetro, migração, bloqueio, corrupção, backups e fluxo de cadastro pela interface.

## Estrutura do projeto

```text
studytonks/
├── main.py
├── app/
│   ├── assets/studytonks.{ico,png,svg}
│   ├── storage/
│   │   ├── schema.py
│   │   └── store.py
│   ├── services/
│   │   ├── study.py
│   │   └── reminders.py
│   └── ui/
│       ├── widgets.py
│       ├── components.py
│       ├── theme.py
│       ├── window.py
│       └── pages/
│           ├── subjects.py
│           ├── notes.py
│           ├── assessments.py
│           ├── study.py
│           ├── agenda.py
│           └── settings.py
├── tests/{conftest.py,test_domain.py,test_ui.py}
├── tools/{create_icon.py,smoke.py,site_manifest.py}
├── packaging/                 # Instalador e validação Windows
├── site/                      # Mini website sem dependências npm
├── docs/data-format.md
├── .github/workflows/{windows,pages}.yml
├── requirements.txt
├── requirements-dev.txt
├── requirements-lock.txt
├── pyproject.toml
└── build.bat
```

## Limites atuais

- Fórmulas LaTeX são editadas e exibidas em texto; não há renderizador matemático.
- O cronômetro faz checkpoints a cada 30 segundos e ao pausar/continuar. Após interrupção abrupta, a sessão reaparece pausada; pode perder até o intervalo desde o último checkpoint. O período com o aplicativo fechado não conta como estudo. Registros encerrados são persistentes.
- A cópia anterior recupera o último snapshot, podendo perder a última alteração. Backups não são criptografados: proteja a pasta ou o ZIP ao compartilhar.
- Importação de backups é limitada a 50 MB descompactados; o cadastro não tem limite de número de matérias.
- O ambiente de entrega é Linux sem desktop Windows. Os testes Qt usam offscreen; não substituem a verificação visual e de integração no Windows.

Projeto original: Studytonks, de devFelipeMRB, criado para acompanhar a evolução semanal de estudos com Python.
