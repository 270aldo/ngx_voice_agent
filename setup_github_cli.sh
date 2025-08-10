#!/bin/bash

# Script para configurar GitHub CLI y hacer push automático
# Autor: NGX Repository Setup

echo "🚀 NGX Repository - Configuración Automática de GitHub CLI"
echo "========================================================"

# Detectar el sistema operativo
OS="$(uname -s)"

# Función para instalar GitHub CLI
install_gh_cli() {
    echo "📦 Instalando GitHub CLI..."
    
    if [[ "$OS" == "Darwin" ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "✅ Homebrew detectado. Instalando GitHub CLI..."
            brew install gh
        else
            echo "❌ Homebrew no encontrado. Instalando Homebrew primero..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            brew install gh
        fi
    elif [[ "$OS" == "Linux" ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt update
            sudo apt install gh
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS
            sudo yum install gh
        else
            echo "❌ Sistema Linux no soportado automáticamente"
            exit 1
        fi
    else
        echo "❌ Sistema operativo no soportado: $OS"
        exit 1
    fi
}

# Verificar si gh está instalado
if ! command -v gh &> /dev/null; then
    install_gh_cli
else
    echo "✅ GitHub CLI ya está instalado"
fi

# Autenticar con GitHub
echo ""
echo "🔐 Configurando autenticación con GitHub..."
echo "Se abrirá tu navegador para autenticarte."
echo ""
gh auth login --web

# Verificar autenticación
if gh auth status &> /dev/null; then
    echo "✅ Autenticación exitosa"
else
    echo "❌ Error en la autenticación"
    exit 1
fi

# Hacer push de la rama
echo ""
echo "📤 Haciendo push de la rama feature/repository-professionalization..."
git push -u origin feature/repository-professionalization

# Crear Pull Request
echo ""
echo "📝 Creando Pull Request..."
gh pr create \
    --base develop \
    --head feature/repository-professionalization \
    --title "feat: profesionalización completa del repositorio" \
    --body "## 🚀 Profesionalización del Repositorio

Este PR implementa una transformación completa del repositorio para alcanzar estándares profesionales.

### ✅ Cambios Realizados:

#### 🧹 Limpieza Masiva (27MB eliminados)
- Eliminación de archivos de logs (14MB)
- Limpieza de resultados de tests
- Eliminación de archivos duplicados (*2.py)
- Reorganización de documentación en \`/docs/archive\`
- **Resultado**: Repositorio reducido de 74MB a 47MB (-36%)

#### 🔧 Configuración Profesional
- **GitFlow** implementado con configuración completa
- **Pre-commit hooks** con 11 verificaciones automáticas
- **Conventional commits** con commitizen
- **CI/CD** con GitHub Actions

#### 🛡️ Seguridad y Calidad
- Escaneo automático de seguridad (Bandit, Trivy)
- Tests automatizados en cada PR
- Linting y formateo de código (Ruff, Black, MyPy)
- Templates para PRs e Issues

#### 📚 Documentación
- CONTRIBUTING.md con guías detalladas
- CODE_OF_CONDUCT.md
- SECURITY.md con política de seguridad
- Estructura organizada en \`/docs\`

### 📊 Métricas de Mejora:
- **Tamaño del repo**: 74MB → 47MB
- **Archivos eliminados**: 150+
- **Checks automatizados**: 11
- **Workflows CI/CD**: 2

### 🔄 Próximos Pasos (Post-Merge):
- [ ] Configurar branch protection rules
- [ ] Habilitar Dependabot
- [ ] Configurar CodeQL
- [ ] Activar secret scanning"

# Obtener URL del PR
PR_URL=$(gh pr view --json url -q .url)

echo ""
echo "✅ ¡Pull Request creado exitosamente!"
echo "📎 URL del PR: $PR_URL"
echo ""
echo "🎯 Próximos pasos:"
echo "1. Revisa el PR en: $PR_URL"
echo "2. Solicita revisión de código si es necesario"
echo "3. Una vez aprobado, haz merge"
echo "4. Configura las reglas de protección de branches"
echo ""
echo "🚀 ¡Tu repositorio está listo para ser profesionalizado!"