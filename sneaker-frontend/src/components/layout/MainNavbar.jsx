import React from 'react';

function MainNavbar({
  currentTab,
  username,
  onGoHome,
  onGoProfile,
  onLogout,
}) {
  const tabStyle = (active) => ({
    padding: '12px 20px',
    border: 'none',
    borderRadius: '999px',
    background: active ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)' : 'transparent',
    color: active ? '#fff' : '#334155',
    fontWeight: active ? '700' : '600',
    cursor: 'pointer',
    fontSize: '15px',
    transition: '0.2s ease',
  });

  return (
    <div className="main-navbar">
      <div className="navbar-left">
        <div className="brand-logo">
          <span className="brand-badge">S</span>
          <span className="brand-text">Sneaker RCM</span>
        </div>

        <div className="navbar-tabs">
          <button onClick={onGoHome} style={tabStyle(currentTab === 'home')}>
            Cửa hàng
          </button>
          <button onClick={onGoProfile} style={tabStyle(currentTab === 'profile')}>
            Hồ sơ
          </button>
        </div>
      </div>

      <div className="navbar-right">
        <div className="welcome-chip">
          Xin chào, <b>{username}</b>
        </div>

        <button className="logout-btn" onClick={onLogout}>
          Đăng xuất
        </button>
      </div>
    </div>
  );
}

export default MainNavbar;