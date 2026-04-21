import React from 'react';

function ProfileSection({
  profileTab,
  setProfileTab,
  recentViewed,
  favoriteItems,
  cartItems,
  purchasedItems,
  loadingProfile,
  onOpenProduct,
  onPurchaseProduct,
}) {
  const tabStyle = (active) => ({
    padding: '10px 16px',
    borderRadius: '999px',
    border: 'none',
    background: active ? '#2563eb' : '#e2e8f0',
    color: active ? '#fff' : '#334155',
    fontWeight: 'bold',
    cursor: 'pointer',
    boxShadow: active ? '0 10px 20px rgba(37,99,235,0.20)' : 'none',
  });

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.9)',
        backdropFilter: 'blur(10px)',
        borderRadius: '20px',
        padding: '26px',
        boxShadow: '0 18px 40px rgba(37,99,235,0.08)',
        border: '1px solid rgba(148,163,184,0.15)',
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: '18px', color: '#0f172a' }}>
        Hồ sơ cá nhân
      </h2>

      <div
        style={{
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
          marginBottom: '22px',
          paddingBottom: '18px',
          borderBottom: '1px solid #e5e7eb',
        }}
      >
        <button onClick={() => setProfileTab('history')} style={tabStyle(profileTab === 'history')}>
          Đã xem ({recentViewed.length})
        </button>

        <button onClick={() => setProfileTab('favorites')} style={tabStyle(profileTab === 'favorites')}>
          Yêu thích ({favoriteItems.length})
        </button>

        <button onClick={() => setProfileTab('cart')} style={tabStyle(profileTab === 'cart')}>
          Giỏ hàng ({cartItems.length})
        </button>

        <button onClick={() => setProfileTab('orders')} style={tabStyle(profileTab === 'orders')}>
          Đã mua ({purchasedItems.length})
        </button>
      </div>

      {loadingProfile ? (
        <p>Đang tải dữ liệu hồ sơ...</p>
      ) : (
        <>
          {profileTab === 'history' && (
            <ProductGrid
              items={recentViewed}
              emptyText="Bạn chưa xem sản phẩm nào."
              buttonText="Xem lại"
              onAction={onOpenProduct}
              showQuantity={false}
            />
          )}

          {profileTab === 'favorites' && (
            <ProductGrid
              items={favoriteItems}
              emptyText="Bạn chưa có sản phẩm yêu thích nào."
              buttonText="Xem lại"
              onAction={onOpenProduct}
              showQuantity={false}
            />
          )}

          {profileTab === 'cart' && (
            <ProductGrid
              items={cartItems}
              emptyText="Giỏ hàng của bạn đang trống."
              buttonText="Mua ngay"
              onAction={(productId) => onPurchaseProduct(productId, 1)}
              buttonColor="#16a34a"
              showQuantity={true}
              quantityLabel="Số lượng trong giỏ"
            />
          )}

          {profileTab === 'orders' && (
            <ProductGrid
              items={purchasedItems}
              emptyText="Bạn chưa có đơn hàng nào."
              buttonText="Mua lại"
              onAction={(productId) => onPurchaseProduct(productId, 1)}
              buttonColor="#0f172a"
              showQuantity={true}
              quantityLabel="Đã mua"
            />
          )}
        </>
      )}
    </div>
  );
}

function ProductGrid({
  items,
  emptyText,
  buttonText,
  onAction,
  buttonColor = '#2563eb',
  showQuantity = false,
  quantityLabel = 'Số lượng',
}) {
  if (!items || items.length === 0) {
    return <p style={{ color: '#64748b' }}>{emptyText}</p>;
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: '18px',
      }}
    >
      {items.map((item) => (
        <div
          key={`${buttonText}-${item.product_id}-${item.quantity ?? 'noqty'}`}
          style={{
            border: '1px solid #e2e8f0',
            borderRadius: '18px',
            padding: '14px',
            background: '#fff',
            boxShadow: '0 10px 24px rgba(15,23,42,0.05)',
          }}
        >
          <div
            style={{
              borderRadius: '14px',
              background: '#f8fafc',
              padding: '10px',
              marginBottom: '10px',
            }}
          >
            <img
              src={item.image_url}
              alt={item.name}
              style={{
                width: '100%',
                height: '170px',
                objectFit: 'contain',
                borderRadius: '10px',
              }}
            />
          </div>

          <div
            style={{
              marginBottom: '8px',
              fontSize: '12px',
              fontWeight: '800',
              textTransform: 'uppercase',
              color: '#2563eb',
              letterSpacing: '0.4px',
            }}
          >
            {item.brand || 'Sneaker'}
          </div>

          <h4
            style={{
              fontSize: '14px',
              lineHeight: 1.45,
              minHeight: '42px',
              overflow: 'hidden',
              margin: '10px 0 10px',
              color: '#111827',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {item.name}
          </h4>

          {showQuantity && (
            <div
              style={{
                marginBottom: '10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 10px',
                borderRadius: '10px',
                background: '#eff6ff',
                color: '#1d4ed8',
                fontSize: '13px',
                fontWeight: '700',
              }}
            >
              <span>{quantityLabel}:</span>
              <span>{item.quantity ?? 1}</span>
            </div>
          )}

          <p style={{ margin: '0 0 12px', color: '#dc2626', fontWeight: '800' }}>
            {Number(item.price).toLocaleString('vi-VN')}$
          </p>

          <button
            onClick={() => onAction(item.product_id)}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '12px',
              border: 'none',
              background: buttonColor,
              color: '#fff',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            {buttonText}
          </button>
        </div>
      ))}
    </div>
  );
}

export default ProfileSection;