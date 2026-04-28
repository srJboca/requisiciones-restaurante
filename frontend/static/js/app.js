function showConfirmModal(text, onConfirm) {
    const overlay = document.getElementById('confirmModal');
    const modalText = document.getElementById('confirmModalText');
    const confirmBtn = document.getElementById('confirmModalBtn');
    
    modalText.innerText = text;
    overlay.classList.add('active');
    
    confirmBtn.onclick = () => {
        closeConfirmModal();
        onConfirm();
    };
}

function closeConfirmModal() {
    const overlay = document.getElementById('confirmModal');
    overlay.classList.remove('active');
}

window.saveOrderDraft = function(items, hasZeroInventory, orderDate, token, apiUrl) {
    const submit = async () => {
        try {
            const res = await fetch(`${apiUrl}/requisitions/draft`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ items, order_date: orderDate })
            });
            
            if (res.ok) {
                alert('Draft saved successfully!');
                window.location.reload();
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail}`);
            }
        } catch (e) {
            alert('Connection error');
        }
    };

    if (hasZeroInventory) {
        showConfirmModal("Are you sure some items have a current inventory of 0?", submit);
    } else {
        submit();
    }
}

window.sendOrderToProduction = function(orderDate, token, apiUrl) {
    showConfirmModal("Are you sure you want to send this order to production? You will not be able to modify it afterwards.", async () => {
        try {
            const res = await fetch(`${apiUrl}/requisitions/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ order_date: orderDate })
            });
            
            if (res.ok) {
                alert('Order sent to production successfully!');
                window.location.reload();
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail}`);
            }
        } catch (e) {
            alert('Connection error');
        }
    });
}

window.processShipping = function(items, orderId, token, apiUrl) {
    const submit = async () => {
        try {
            const res = await fetch(`${apiUrl}/production/${orderId}/ship`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ items })
            });
            
            if (res.ok) {
                alert('Order shipped successfully!');
                window.location.reload();
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail}`);
            }
        } catch (e) {
            alert('Connection error');
        }
    };
    submit();
}

window.processReceiving = function(items, orderId, token, apiUrl) {
    const submit = async () => {
        try {
            const res = await fetch(`${apiUrl}/requisitions/${orderId}/receive`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ items })
            });
            
            if (res.ok) {
                alert('Order closed successfully!');
                window.location.reload();
            } else {
                const data = await res.json();
                alert(`Error: ${data.detail}`);
            }
        } catch (e) {
            alert('Connection error');
        }
    };
    submit();
}
