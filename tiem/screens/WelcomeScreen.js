import React from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  Linking,
} from 'react-native';

export default function WelcomeScreen({ navigation }) {
  const handleGoogleLogin = () => {
    Linking.openURL('http://127.0.0.1:8000/auth/google/');
  };

  const handleFacebookLogin = () => {
    Linking.openURL('http://127.0.0.1:8000/auth/facebook/');
  };

  return (
    <View style={styles.container}>
      <Image
        source={require('../assets/logo.png')} // make sure to add logo.png in assets folder
        style={styles.logo}
      />
      <Text style={styles.title}>Welcome to Our TIEM</Text>
      <Text style={styles.subtitle}>Join the community and explore amazing content.</Text>

      <TouchableOpacity
        style={styles.createAccountButton}
        onPress={() => navigation.navigate('Signup')}>
        <Text style={styles.createAccountText}>Create Account</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.socialButton} onPress={handleGoogleLogin}>
        <Image source={require('../assets/google-icon.png')} style={styles.socialIcon} />
        <Text style={styles.socialText}>Google</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.socialButton} onPress={handleFacebookLogin}>
        <Image source={require('../assets/Facebook-icon.png')} style={styles.socialIcon} />
        <Text style={styles.socialText}>Facebook</Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => navigation.navigate('Login')}>
        <Text style={styles.loginLink}>Already have an account? Sign in</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    paddingHorizontal: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    width: 120,
    height: 120,
    resizeMode: 'contain',
    marginBottom: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#222',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#555',
    marginBottom: 30,
    textAlign: 'center',
  },
  createAccountButton: {
    backgroundColor: '#ff2d55',
    paddingVertical: 15,
    paddingHorizontal: 40,
    borderRadius: 10,
    marginBottom: 20,
  },
  createAccountText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  socialButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f1f1',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginBottom: 15,
    width: '100%',
  },
  socialIcon: {
    width: 24,
    height: 24,
    marginRight: 10,
  },
  socialText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  loginLink: {
    marginTop: 25,
    color: '#888',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
});
