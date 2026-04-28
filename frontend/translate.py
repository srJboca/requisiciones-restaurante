import polib

translations = {
    "Admin Dashboard": "Panel de Administración",
    "System Settings": "Configuración del Sistema",
    "Requisition ETA (Business Days)": "ETA de Requisición (Días Hábiles)",
    "Default Language": "Idioma Predeterminado",
    "English": "Inglés",
    "Spanish": "Español",
    "Save Settings": "Guardar Configuración",
    "Change Password": "Cambiar Contraseña",
    "Logout": "Cerrar Sesión",
    "Login": "Iniciar Sesión",
    "Order Builder": "Creador de Pedidos",
    "Receiving": "Recepción",
    "Shipping": "Envíos",
    "Current Password": "Contraseña Actual",
    "New Password": "Nueva Contraseña",
    "Confirm New Password": "Confirmar Nueva Contraseña",
    "Cancel": "Cancelar",
    "Update Password": "Actualizar Contraseña",
    "Save Changes": "Guardar Cambios",
    "Username": "Nombre de Usuario",
    "Password": "Contraseña",
    "Sign In": "Ingresar",
    "Production Plant Shipping": "Envíos Planta de Producción",
    "Filter by Date": "Filtrar por Fecha",
    "Clear Filter": "Limpiar Filtro",
    "No pending requirements found.": "No se encontraron requerimientos pendientes.",
    "Order #": "Pedido #",
    "Date": "Fecha",
    "Submitted by": "Enviado por",
    "SKU": "SKU",
    "Product Name": "Nombre del Producto",
    "Current Inv": "Inv. Actual",
    "Required Qty": "Cant. Requerida",
    "Shipped Qty": "Cant. Enviada",
    "Ship Order": "Enviar Pedido",
    "Daily Requisition Builder": "Constructor de Requisiciones Diarias",
    "Requisition Date": "Fecha de Requisición",
    "Filter by Product Group": "Filtrar por Grupo",
    "All Groups": "Todos los Grupos",
    "Status": "Estado",
    "Shipped by": "Enviado por",
    "Closed by": "Cerrado por",
    "Delivery ETA": "Tiempo estimado de entrega",
    "Calculating...": "Calculando...",
    "Draft": "Borrador",
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
    "Submitted": "Enviado",
    "Shipped": "Enviado",
    "Closed": "Cerrado",
    "No past requisitions found.": "No se encontraron requisiciones pasadas.",
    "Restaurant Receiving": "Recepción de Restaurante",
    "No shipped orders found for receiving.": "No se encontraron pedidos enviados para recepción.",
    "Received Qty": "Cant. Recibida",
    "Confirm Receipt": "Confirmar Recepción",
    "Welcome to ReqSys": "Bienvenido a ReqSys",
    "The centralized restaurant requisition management system.": "El sistema centralizado de gestión de requisiciones para restaurantes.",
    "Login to Continue": "Inicie Sesión para Continuar"
}

po = polib.pofile('translations/es/LC_MESSAGES/messages.po')
for entry in po:
    if entry.msgid in translations:
        entry.msgstr = translations[entry.msgid]
    else:
        # Provide a default or keep original
        entry.msgstr = entry.msgid

po.save()
print("Translations applied.")
