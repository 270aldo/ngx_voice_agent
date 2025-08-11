# Instrucciones para Aplicar Migración 013 - Fix Security Definer Views

## 🎯 Objetivo
Esta migración corrige 48 errores de SECURITY DEFINER en 10 vistas de la base de datos, además de resolver problemas de consistencia con la columna variant_id.

## 📋 Pasos para Aplicar la Migración

### Opción 1: Usando Supabase Dashboard (Recomendado)

1. **Accede al Supabase Dashboard**
   - Ve a tu proyecto en https://app.supabase.com

2. **Navega al SQL Editor**
   - En el menú lateral, haz clic en "SQL Editor"

3. **Crea una nueva consulta**
   - Haz clic en "New query"

4. **Copia el contenido de la migración**
   - Abre el archivo `migration_013_only.sql` 
   - Copia TODO el contenido

5. **Pega y ejecuta**
   - Pega el contenido en el editor SQL
   - Haz clic en "Run" o presiona Cmd/Ctrl + Enter

6. **Verifica los resultados**
   - Deberías ver mensajes como:
     - "✅ Migración 013 completada"
     - "📊 Total de vistas: [número]"
     - "🔒 Vistas con SECURITY DEFINER: 0"

### Opción 2: Usando Supabase CLI

```bash
# Si tienes Supabase CLI configurado localmente:
supabase db push < migration_013_only.sql
```

## ✅ Verificación Post-Migración

1. **Verifica en Security Advisor**
   - Ve a Supabase Dashboard > Database > Security Advisor
   - Los 48 errores de "Views with security definer" deberían desaparecer

2. **Prueba las vistas actualizadas**
   Las siguientes vistas han sido actualizadas:
   - `top_performing_prompts`
   - `model_performance_view`
   - `training_activity_view`
   - `emotional_summary_view`
   - `effective_patterns_view`
   - `genetic_evolution_view`
   - `trial_performance_by_tier`
   - `demo_effectiveness`
   - `effective_touchpoints`
   - `roi_by_profession_view`

3. **Verifica que las aplicaciones funcionen correctamente**
   - Las vistas ahora usan `security_invoker = true`
   - Esto significa que se ejecutan con los permisos del usuario que las invoca
   - Asegúrate de que los usuarios tengan los permisos necesarios

## 🚨 Resolución de Problemas

### Si ves errores de "relation does not exist":
- Esto es normal para vistas que se están recreando
- La migración usa DROP IF EXISTS para manejar esto

### Si ves errores de permisos:
- Asegúrate de estar ejecutando con un usuario que tenga permisos de CREATE VIEW
- Generalmente necesitas usar el usuario service_role o postgres

### Si las aplicaciones dejan de funcionar:
- Verifica que los roles `authenticated` y `anon` tengan permisos SELECT en las vistas
- La migración incluye GRANTs automáticos, pero puedes ejecutar manualmente:
  ```sql
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
  ```

## 📊 Cambios Realizados

1. **Corrección de SECURITY DEFINER**
   - Todas las vistas ahora usan `WITH (security_invoker = true)`
   - Esto es más seguro y evita problemas de escalación de privilegios

2. **Normalización de variant_id**
   - Se asegura consistencia entre tablas que usan variant_id
   - Maneja casos donde variant_id es UUID o VARCHAR

3. **Índices de Performance**
   - Se agregan índices para mejorar el rendimiento de las vistas
   - Especialmente importante para JOINs frecuentes

4. **Permisos Actualizados**
   - Se otorgan permisos SELECT a roles authenticated y service_role
   - Asegura que las aplicaciones puedan acceder a las vistas

## 📝 Notas Importantes

- Esta migración es **idempotente**: se puede ejecutar múltiples veces sin problemas
- Los cambios son **compatibles hacia atrás**: las aplicaciones existentes seguirán funcionando
- La migración **no modifica datos**, solo estructuras de vistas e índices

## 🎉 Resultado Esperado

Después de aplicar esta migración:
- ✅ 0 errores en Security Advisor relacionados con SECURITY DEFINER
- ✅ Todas las vistas usando security_invoker = true
- ✅ Mejor performance con los nuevos índices
- ✅ Consistencia en el manejo de variant_id