import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';

import AuthForm from './components/auth/AuthForm';
import MainNavbar from './components/layout/MainNavbar';
import StoreSection from './components/store/StoreSection';
import ProfileSection from './components/profile/ProfileSection';
import ProductDetailPage from './components/products/ProductDetailPage';

import { loginUser, registerUser } from './services/authService';
import {
  fetchHomepageProductsApi,
  interactProductApi,
} from './services/productService';
import {
  fetchCartApi,
  fetchFavoritesApi,
  fetchOrdersApi,
  fetchRecentViewedApi,
} from './services/userService';

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [loadingAuth, setLoadingAuth] = useState(false);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('Nam');

  const [products, setProducts] = useState([]);
  const [homepageType, setHomepageType] = useState('default');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadingProducts, setLoadingProducts] = useState(false);

  const [profileTab, setProfileTab] = useState('history');
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [recentViewed, setRecentViewed] = useState([]);
  const [favoriteItems, setFavoriteItems] = useState([]);
  const [cartItems, setCartItems] = useState([]);
  const [purchasedItems, setPurchasedItems] = useState([]);

  const currentTab = location.pathname.startsWith('/profile') ? 'profile' : 'home';

  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUsername = localStorage.getItem('username');

    if (token) {
      setIsLoggedIn(true);
      setUsername(savedUsername || '');
    }
  }, []);

  useEffect(() => {
    if (isLoggedIn && location.pathname === '/') {
      fetchHomepageProducts(page);
    }
  }, [isLoggedIn, page, location.pathname]);

  const resetAuthForm = () => {
    setPassword('');
    setAge('');
    setGender('Nam');
  };

  const handleToggleMode = () => {
    setIsLoginMode((prev) => !prev);
    resetAuthForm();
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoadingAuth(true);

    try {
      await registerUser({
        username,
        password,
        age: parseInt(age, 10),
        gender,
      });

      alert('Đăng ký thành công! Vui lòng đăng nhập.');
      setIsLoginMode(true);
      resetAuthForm();
    } catch (err) {
      const detail = err.response?.data?.detail;
      alert(
        typeof detail === 'string'
          ? detail
          : 'Đăng ký thất bại. Vui lòng kiểm tra lại dữ liệu.'
      );
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoadingAuth(true);

    try {
      const data = await loginUser({ username, password });
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('username', username);

      setIsLoggedIn(true);
      setPage(1);
      await fetchProfileData();
      navigate('/');
    } catch (err) {
      const detail = err.response?.data?.detail;
      alert(
        typeof detail === 'string'
          ? detail
          : 'Đăng nhập thất bại. Sai tài khoản hoặc mật khẩu.'
      );
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');

    setIsLoggedIn(false);
    setIsLoginMode(true);
    setUsername('');
    setPassword('');
    setAge('');
    setGender('Nam');

    setProducts([]);
    setHomepageType('default');
    setPage(1);
    setTotalPages(1);

    setProfileTab('history');
    setRecentViewed([]);
    setFavoriteItems([]);
    setCartItems([]);
    setPurchasedItems([]);

    navigate('/');
  };

  const fetchHomepageProducts = async (nextPage = 1) => {
    setLoadingProducts(true);
    try {
      const data = await fetchHomepageProductsApi(nextPage, 30);
      setProducts(data.items || []);
      setHomepageType(data.type || 'default');
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      console.error('fetchHomepageProducts error:', err);
      alert('Không tải được sản phẩm trang chủ.');
    } finally {
      setLoadingProducts(false);
    }
  };

  const fetchProfileData = async () => {
    setLoadingProfile(true);
    try {
      const [recentData, favoriteData, cartData, orderData] = await Promise.all([
        fetchRecentViewedApi(),
        fetchFavoritesApi(),
        fetchCartApi(),
        fetchOrdersApi(),
      ]);

      setRecentViewed(recentData || []);
      setFavoriteItems(favoriteData || []);
      setCartItems(cartData || []);
      setPurchasedItems(orderData || []);
    } catch (err) {
      console.error('fetchProfileData error:', err);
    } finally {
      setLoadingProfile(false);
    }
  };

  const openProductDetail = (productId) => {
    navigate(`/product/${productId}`);
  };

  const handleLike = async (productId) => {
    try {
      await interactProductApi(productId, 'like', 1);
      await fetchProfileData();
      alert('Đã thêm vào yêu thích!');
      return true;
    } catch (err) {
      console.error('like error:', err);
      alert('Không thể thêm vào yêu thích.');
      return false;
    }
  };

  const handleAddToCart = async (productId, quantity = 1) => {
    try {
      await interactProductApi(productId, 'add_to_cart', quantity);
      await fetchProfileData();
      alert(`Đã thêm ${quantity} sản phẩm vào giỏ hàng!`);
      return true;
    } catch (err) {
      console.error('add_to_cart error:', err);
      alert('Không thể thêm vào giỏ hàng.');
      return false;
    }
  };

  const handlePurchase = async (productId, quantity = 1) => {
    try {
      await interactProductApi(productId, 'purchase', quantity);
      await fetchProfileData();
      alert(`Mua ${quantity} sản phẩm thành công!`);
      return true;
    } catch (err) {
      console.error('purchase error:', err);
      alert('Không thể mua sản phẩm.');
      return false;
    }
  };

  if (!isLoggedIn) {
    return (
      <AuthForm
        isLoginMode={isLoginMode}
        username={username}
        password={password}
        age={age}
        gender={gender}
        onUsernameChange={setUsername}
        onPasswordChange={setPassword}
        onAgeChange={setAge}
        onGenderChange={setGender}
        onSubmit={isLoginMode ? handleLogin : handleRegister}
        onToggleMode={handleToggleMode}
        loading={loadingAuth}
      />
    );
  }

  return (
    <div className="app-shell">
      <div className="app-overlay" />
      <div className="app-container">
        <MainNavbar
          currentTab={currentTab}
          username={username}
          onGoHome={() => {
            setPage(1);
            navigate('/');
          }}
          onGoProfile={() => {
            fetchProfileData();
            navigate('/profile');
          }}
          onLogout={handleLogout}
        />

        <Routes>
          <Route
            path="/"
            element={
              <StoreSection
                products={products}
                page={page}
                totalPages={totalPages}
                loading={loadingProducts}
                onViewProduct={openProductDetail}
                onPrevPage={() => setPage((prev) => Math.max(1, prev - 1))}
                onNextPage={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                onGoPage={setPage}
                homepageType={homepageType}
              />
            }
          />

          <Route
            path="/profile"
            element={
              <ProfileSection
                profileTab={profileTab}
                setProfileTab={setProfileTab}
                recentViewed={recentViewed}
                favoriteItems={favoriteItems}
                cartItems={cartItems}
                purchasedItems={purchasedItems}
                loadingProfile={loadingProfile}
                onOpenProduct={openProductDetail}
                onPurchaseProduct={handlePurchase}
              />
            }
          />

          <Route
            path="/product/:id"
            element={
              <ProductDetailPage
                onLike={handleLike}
                onAddToCart={handleAddToCart}
                onPurchase={handlePurchase}
                onOpenProduct={openProductDetail}
              />
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  return <AppContent />;
}