import React from 'react';

function AuthForm({
  isLoginMode,
  username,
  password,
  age,
  gender,
  onUsernameChange,
  onPasswordChange,
  onAgeChange,
  onGenderChange,
  onSubmit,
  onToggleMode,
  loading,
}) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f5f7fb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          width: '100%',
          maxWidth: '420px',
          background: '#fff',
          borderRadius: '16px',
          padding: '32px',
          boxShadow: '0 12px 30px rgba(0,0,0,0.08)',
        }}
      >
        <h2
          style={{
            marginTop: 0,
            marginBottom: '24px',
            textAlign: 'center',
            color: '#222',
          }}
        >
          {isLoginMode ? 'Đăng nhập' : 'Đăng ký tài khoản'}
        </h2>

        <div style={{ marginBottom: '14px' }}>
          <label
            style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 'bold',
              color: '#333',
            }}
          >
            Tên tài khoản
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => onUsernameChange(e.target.value)}
            placeholder="Nhập tên tài khoản"
            required
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '10px',
              border: '1px solid #d9dee8',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ marginBottom: '14px' }}>
          <label
            style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 'bold',
              color: '#333',
            }}
          >
            Mật khẩu
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            placeholder="Nhập mật khẩu"
            required
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '10px',
              border: '1px solid #d9dee8',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {!isLoginMode && (
          <>
            <div style={{ marginBottom: '14px' }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: '8px',
                  fontWeight: 'bold',
                  color: '#333',
                }}
              >
                Tuổi
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => onAgeChange(e.target.value)}
                placeholder="Nhập tuổi"
                min="10"
                max="100"
                required
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '1px solid #d9dee8',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: '8px',
                  fontWeight: 'bold',
                  color: '#333',
                }}
              >
                Giới tính
              </label>
              <select
                value={gender}
                onChange={(e) => onGenderChange(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '1px solid #d9dee8',
                  boxSizing: 'border-box',
                }}
              >
                <option value="Nam">Nam</option>
                <option value="Nữ">Nữ</option>
                <option value="Khác">Khác</option>
              </select>
            </div>
          </>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '10px',
            border: 'none',
            background: isLoginMode ? '#2563eb' : '#16a34a',
            color: '#fff',
            fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading
            ? 'Đang xử lý...'
            : isLoginMode
            ? 'Đăng nhập'
            : 'Đăng ký'}
        </button>

        <p
          style={{
            marginTop: '18px',
            textAlign: 'center',
            color: '#666',
            fontSize: '14px',
          }}
        >
          {isLoginMode ? 'Chưa có tài khoản? ' : 'Đã có tài khoản? '}
          <span
            onClick={onToggleMode}
            style={{
              color: '#2563eb',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            {isLoginMode ? 'Đăng ký ngay' : 'Đăng nhập'}
          </span>
        </p>
      </form>
    </div>
  );
}

export default AuthForm;