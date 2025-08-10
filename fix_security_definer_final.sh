#!/bin/bash

echo "🔧 ELIMINANDO ERRORES DE SECURITY DEFINER..."
echo ""

# Crear archivo SQL temporal con las queries
cat > /tmp/identify_views.sql << 'EOF'
-- Identificar vistas con SECURITY DEFINER
SELECT 
    'DROP VIEW IF EXISTS public.' || viewname || ' CASCADE;' as drop_command,
    viewname
FROM pg_views
WHERE schemaname = 'public'
AND definition LIKE '%SECURITY DEFINER%'
ORDER BY viewname;
EOF

echo "1. Identificando vistas con SECURITY DEFINER..."
echo ""

# Ejecutar la query para identificar vistas
supabase db execute -f /tmp/identify_views.sql > /tmp/views_to_drop.txt

# Mostrar las vistas encontradas
echo "Vistas encontradas con SECURITY DEFINER:"
cat /tmp/views_to_drop.txt
echo ""

# Extraer solo los comandos DROP
grep "DROP VIEW" /tmp/views_to_drop.txt | sed 's/|.*//g' | sed 's/^ *//' > /tmp/drop_commands.sql

# Contar vistas
VIEW_COUNT=$(grep -c "DROP VIEW" /tmp/drop_commands.sql 2>/dev/null || echo 0)

if [ "$VIEW_COUNT" -gt 0 ]; then
    echo "⚠️  Se encontraron $VIEW_COUNT vistas con SECURITY DEFINER"
    echo ""
    echo "Comandos a ejecutar:"
    cat /tmp/drop_commands.sql
    echo ""
    
    read -p "¿Deseas eliminar estas vistas? (s/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo ""
        echo "2. Eliminando vistas..."
        
        # Ejecutar los comandos DROP
        supabase db execute -f /tmp/drop_commands.sql
        
        echo ""
        echo "✅ Vistas eliminadas"
        
        # Verificar si quedan vistas
        echo ""
        echo "3. Verificando si quedan vistas con SECURITY DEFINER..."
        supabase db execute -f /tmp/identify_views.sql | grep -c "DROP VIEW" || echo "✅ No quedan vistas con SECURITY DEFINER"
        
    else
        echo ""
        echo "❌ Operación cancelada"
    fi
else
    echo "✅ No se encontraron vistas con SECURITY DEFINER"
fi

# Limpiar archivos temporales
rm -f /tmp/identify_views.sql /tmp/views_to_drop.txt /tmp/drop_commands.sql

echo ""
echo "💡 Próximos pasos:"
echo "   1. Ejecuta: supabase db push --dry-run"
echo "   2. Si todo está bien: supabase db push"
echo "   3. Verifica en el Security Advisor del dashboard"