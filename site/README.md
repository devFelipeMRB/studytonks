# Site de instalação do Studytonks

Landing page estática em português. Não exige npm, servidor de aplicação, fontes externas ou cookies. Abra `index.html` no navegador para consultar o conteúdo; para hospedar, publique esta pasta no GitHub Pages.

## Publicação e downloads

A página não apresenta um download direto como disponível até confirmar um instalador publicado. Ela consulta primeiro `release.json` do site. Se o manifesto não confirmar a disponibilidade, consulta a API pública do GitHub em `https://api.github.com/repos/devFelipeMRB/studytonks/releases/latest`. Erros, bloqueios, limite da API e ausência de release mantêm o estado **Instalador em preparação**, com um link funcional para a página de versões.

O pipeline de release deve publicar os binários Windows e, somente após essa publicação ter sucesso, gerar o manifesto abaixo no artefato do site:

```json
{
  "available": true,
  "version": "v1.0.0",
  "installer_url": "https://github.com/devFelipeMRB/studytonks/releases/download/v1.0.0/Studytonks-Setup.exe",
  "portable_url": "https://github.com/devFelipeMRB/studytonks/releases/download/v1.0.0/Studytonks-Portable.zip"
}
```

Use URLs específicas da versão, evitando que um manifesto antigo confirme um artefato de uma versão diferente. O manifesto inicial mantém `available: false`. O JavaScript aceita somente downloads HTTPS do próprio repositório, com os nomes exatos acima. Se a versão portátil não for publicada, use `portable_url: null`.

Publique `site/` como artefato `github-pages`, usando `actions/upload-pages-artifact` e `actions/deploy-pages`. Nas configurações do repositório, **Pages → Source → GitHub Actions** precisa estar habilitado. A página é projetada para `https://devFelipeMRB.github.io/studytonks/`; essa URL só estará disponível após uma implantação bem-sucedida.

## Assets e privacidade

- Ícone original copiado de `app/assets/studytonks.svg`.
- `assets/dashboard.png` é uma captura da interface real em uma pasta temporária vazia, sem dados pessoais ou notas inventadas.
- Nenhum analytics, formulário ou armazenamento de dados de estudo. A única preferência no navegador é o tema, salvo em `localStorage` quando permitido.
- A consulta de versão exige conexão; o aplicativo desktop instalado funciona offline.

## Verificação

```bash
node --check site/app.js
node site/verify.js
```

É possível servir a pasta internamente para testar HTML, responsividade, temas e estados de disponibilidade com um navegador automatizado. A disponibilidade do instalador deve ser testada com manifesto válido, manifesto ausente, API com release, API sem release e falha de rede.
