# Instalação no Home Assistant

Esta é uma integração personalizada, não uma aplicação/add-on do Supervisor.

## Pelo HACS

1. Abrir **HACS → menu → Repositórios personalizados**.
2. Adicionar `https://github.com/spkon/ha_google_wifi`, tipo **Integração**.
3. Descarregar **Google WiFi Insights** e reiniciar o HA.
4. Em **Definições → Dispositivos e serviços → Adicionar integração**, procurar
   **Google WiFi Insights**.
5. Escolher conta Google para clientes/métricas, ou estado local dos pontos.
6. Abrir **Google WiFi** na barra lateral. Mapa e visão geral são instalados
   automaticamente; não é necessário copiar JavaScript ou editar YAML.

## Conta Google

Seguir o [fluxo alternativo gpsoauth](https://github.com/simon-weber/gpsoauth#alternative-flow):
autenticar pessoalmente em `https://accounts.google.com/EmbeddedSetup`, ler os
termos e aceitá-los se concordar. Mesmo que a página continue a carregar,
procurar `oauth_token` em **F12 → Application → Storage → Cookies → accounts.google.com**.
Sem esse cookie, a autenticação ainda não está concluída. Introduzir email e
token diretamente no formulário HA, mantendo o Android ID gerado.

Não enviar tokens por chat/issues ou incluí-los em ficheiros partilhados.
Ficam na configuração do HA, que também exige proteção dos backups.

## Instalação manual e atualização

Copiar a pasta completa `custom_components/google_wifi_insights`, incluindo
`frontend/`, para `/config/custom_components`. Reiniciar o HA e configurar a
integração. As atualizações pelo HACS incluem os ficheiros do mapa; reiniciar o
HA e recarregar o navegador. Os painéis manuais existentes são preservados.

Estado local permite 1–10 IPv4 privados reais, no formato `Nome=IP`, um por linha.
Conta Google e estado local podem coexistir. Sem conta Google não há lista de
clientes. Sinal cinzento significa leitura em falta; períodos sem utilização
recebida permanecem desconhecidos. As janelas de consumo são móveis, não «hoje».

Consultar [o inventário](CAPABILITIES.md) para métricas, ações e limites. O acesso
Google é não oficial; não se afirma suporte para todos os modelos ou funções.
