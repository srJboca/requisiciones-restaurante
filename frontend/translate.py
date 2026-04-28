import polib

translations = {
    # --- base.html ---
    "Admin Dashboard": "Panel de Administración",
    "Order Builder": "Creador de Pedidos",
    "Receiving": "Recepción",
    "Shipping": "Envíos",
    "History": "Historial",
    "Change Password": "Cambiar Contraseña",
    "Logout": "Cerrar Sesión",
    "Login": "Ingresar",
    "Current Password": "Contraseña Actual",
    "New Password": "Nueva Contraseña",
    "Confirm New Password": "Confirmar Nueva Contraseña",
    "Cancel": "Cancelar",
    "Save Changes": "Guardar Cambios",

    # --- welcome.html ---
    "La Cesta - Café Local": "La Cesta - Café Local",
    "The centralized restaurant requisition management system.": "El sistema centralizado de gestión de requisiciones para restaurantes.",
    "Login\n        to Continue": "Ingresar",
    "Login to Continue": "Ingresar",

    # --- login.html ---
    "Username": "Usuario",
    "Password": "Contraseña",

    # --- admin_dashboard.html ---
    "System Settings": "Configuración del Sistema",
    "Requisition ETA (Business Days)": "ETA de Requisición (Días Hábiles)",
    "Default Language": "Idioma Predeterminado",
    "English": "Inglés",
    "Spanish": "Español",
    "Save Settings": "Guardar Configuración",

    # --- restaurant_order.html ---
    "Daily Requisition Builder": "Constructor de Requisiciones Diarias",
    "Requisition Date": "Fecha de Requisición",
    "Filter by Product Group": "Filtrar por Grupo de Producto",
    "All Groups": "Todos los Grupos",
    "Status": "Estado",
    "Submitted by": "Enviado por",
    "Shipped by": "Enviado por",
    "Closed by": "Cerrado por",
    "Delivery ETA": "Tiempo estimado de entrega",
    "Calculating...": "Calculando...",
    "Draft": "Borrador",
    "Submitted": "Enviado",
    "Shipped": "Enviado",
    "Closed": "Cerrado",
    "SKU": "SKU",
    "Product Name": "Nombre del Producto",
    "Unit Measure": "Unidad de Medida",
    "Current Inventory": "Inventario Actual",
    "Required Quantity": "Cantidad Requerida",
    "Edited By": "Editado Por",
    "Save Draft": "Guardar Borrador",
    "Send to Production": "Enviar a Producción",
    "Order for": "Pedido para",
    "has been": "ha sido",
    "Requisitions Report": "Reporte de Requisiciones",
    "Order Date": "Fecha de Pedido",
    "Action By": "Acción por",
    "Total Items": "Total de Artículos",
    "No past requisitions found.": "No se encontraron requisiciones pasadas.",

    # --- production_shipping.html ---
    "Production Plant Shipping": "Envíos Planta de Producción",
    "Filter by Date": "Filtrar por Fecha",
    "Clear Filter": "Limpiar Filtro",
    "No pending requirements found.": "No se encontraron requerimientos pendientes.",
    "Order #": "Pedido #",
    "Date": "Fecha",
    "Current Inv": "Inv. Actual",
    "Required Qty": "Cant. Requerida",
    "Shipped Qty": "Cant. Enviada",
    "Ship Order": "Enviar Pedido",

    # --- restaurant_receiving.html ---
    "Restaurant Receiving": "Recepción de Restaurante",
    "No shipped orders found for receiving.": "No se encontraron pedidos enviados para recepción.",
    "Received Qty": "Cant. Recibida",
    "Confirm Receipt": "Confirmar Recepción",

    # --- history.html ---
    "View Details": "Ver Detalles",
    "View\n                Details": "Ver Detalles",
    "items": "artículos",
}

po = polib.pofile('translations/es/LC_MESSAGES/messages.po')

matched = 0
unmatched = []

for entry in po:
    if entry.msgid in translations:
        entry.msgstr = translations[entry.msgid]
        matched += 1
    else:
        # Keep existing translation if already set, otherwise flag it
        if not entry.msgstr:
            entry.msgstr = entry.msgid  # Fallback to original
        unmatched.append(repr(entry.msgid))

po.save()
print(f"Done. {matched} translated, {len(unmatched)} unmatched:")
for u in unmatched:
    print(f"  UNMATCHED: {u}")
