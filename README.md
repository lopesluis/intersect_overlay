# Interseção Overlay (QGIS Plugin)

Plugin para QGIS que gera uma camada temporária da interseção entre duas camadas poligonais,
calculando automaticamente:
- Área em metros quadrados (m²)
- Área em hectares (ha)
- Perímetro em metros (m)

## Requisitos
- QGIS 3.22 ou superior
- Camadas do tipo polígono
- Projeto configurado em sistema de coordenadas projetado em metros (ex.: UTM / SIRGAS 2000)

## Como usar
1. Carregue duas camadas poligonais no QGIS
2. Abra o plugin pelo menu **Plugins → Interseção Overlay**
3. Selecione a camada base e a camada de sobreposição
4. Clique em **Executar**
5. A camada de interseção será criada como camada temporária

## Observações
- O plugin valida se o sistema de referência de coordenadas está em metros
- Não grava arquivos no disco automaticamente

## Licença
MIT License
