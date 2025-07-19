import React, { useState, useEffect, useRef } from 'react';
import { View, Text, FlatList, Image, TouchableOpacity, StyleSheet, Modal, TextInput, ScrollView, ActivityIndicator } from 'react-native';
import { Video } from 'expo-av';
import { useNavigation } from '@react-navigation/native';
import { MaterialIcons, FontAwesome, Feather, Ionicons } from '@expo/vector-icons';

// Main Feed Screen
const FeedScreen = () => {
  const [activeTab, setActiveTab] = useState('reel');
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPost, setSelectedPost] = useState(null);
  const [commentText, setCommentText] = useState('');
  const [commentsVisible, setCommentsVisible] = useState(false);
  const navigation = useNavigation();

  // Fetch posts from API
  const fetchPosts = async () => {
    try {
      setRefreshing(true);
      // Replace with actual API call
      const response = await fetch(`/api/feed/?tab=${activeTab}`);
      const data = await response.json();
      setPosts(data.results);
    } catch (error) {
      console.error('Error fetching posts:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, [activeTab]);

  const handleLike = async (postId) => {
    // Implement like functionality
  };

  const handleFollow = async (username) => {
    // Implement follow functionality
  };

  const openComments = (post) => {
    setSelectedPost(post);
    setCommentsVisible(true);
  };

  const postComment = async () => {
    if (commentText.trim()) {
      // Implement comment posting
      setCommentText('');
    }
  };

  const renderItem = ({ item }) => (
    <PostItem 
      item={item} 
      onLike={handleLike} 
      onFollow={handleFollow} 
      onCommentPress={openComments}
    />
  );

  return (
    <View style={styles.container}>
      {/* Tab Bar */}
      <View style={styles.tabBar}>
        <TabButton 
          icon="compass" 
          label="Reel" 
          active={activeTab === 'reel'} 
          onPress={() => setActiveTab('reel')} 
        />
        <TabButton 
          icon="user-friends" 
          label="Following" 
          active={activeTab === 'following'} 
          onPress={() => setActiveTab('following')} 
        />
        <TabButton 
          icon="signal" 
          label="Live" 
          active={activeTab === 'live'} 
          onPress={() => setActiveTab('live')} 
        />
      </View>

      {/* Posts List */}
      {loading ? (
        <ActivityIndicator size="large" style={styles.loader} />
      ) : (
        <FlatList
          data={posts}
          renderItem={renderItem}
          keyExtractor={item => item.id.toString()}
          refreshing={refreshing}
          onRefresh={fetchPosts}
          ListEmptyComponent={<Text style={styles.noPosts}>No posts available</Text>}
        />
      )}

      {/* Comments Modal */}
      <Modal
        visible={commentsVisible}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setCommentsVisible(false)}
      >
        {selectedPost && (
          <CommentSection 
            post={selectedPost} 
            onClose={() => setCommentsVisible(false)}
            commentText={commentText}
            setCommentText={setCommentText}
            onPostComment={postComment}
          />
        )}
      </Modal>
    </View>
  );
};

// Post Item Component
const PostItem = ({ item, onLike, onFollow, onCommentPress }) => {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLiked, setIsLiked] = useState(item.is_liked);
  const [likesCount, setLikesCount] = useState(item.likes_count);

  const togglePlay = () => {
    if (isPlaying) {
      videoRef.current.pauseAsync();
    } else {
      videoRef.current.playAsync();
    }
    setIsPlaying(!isPlaying);
  };

  const handleLikePress = () => {
    setIsLiked(!isLiked);
    setLikesCount(prev => isLiked ? prev - 1 : prev + 1);
    onLike(item.id);
  };

  return (
    <View style={styles.postContainer}>
      {/* User Info */}
      <View style={styles.userInfo}>
        <Image 
          source={{ uri: item.user.profile_picture || 'https://via.placeholder.com/40' }} 
          style={styles.profilePic}
        />
        <Text style={styles.username}>@{item.user.username}</Text>
        {!item.is_current_user && (
          <TouchableOpacity 
            style={[styles.followButton, item.is_following && styles.followingButton]}
            onPress={() => onFollow(item.user.username)}
          >
            <Text style={[styles.followText, item.is_following && styles.followingText]}>
              {item.is_following ? 'Following' : 'Follow'}
            </Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Media Content */}
      <TouchableOpacity onPress={togglePlay} activeOpacity={0.9}>
        {item.content_type === 'video' ? (
          <Video
            ref={videoRef}
            source={{ uri: item.media_file }}
            style={styles.media}
            resizeMode="cover"
            isLooping
            shouldPlay={false}
            useNativeControls={false}
          />
        ) : (
          <Image 
            source={{ uri: item.media_file }} 
            style={styles.media} 
            resizeMode="cover"
          />
        )}
        
        <View style={styles.overlay} />
        <View style={styles.viewCount}>
          <Feather name="eye" size={14} color="white" />
          <Text style={styles.viewCountText}>{item.views.toLocaleString()} views</Text>
        </View>
      </TouchableOpacity>

      {/* Action Buttons */}
      <View style={styles.actionButtons}>
        <TouchableOpacity style={styles.actionButton} onPress={handleLikePress}>
          <FontAwesome 
            name={isLiked ? "heart" : "heart-o"} 
            size={24} 
            color={isLiked ? "#ff3040" : "white"} 
          />
          <Text style={styles.actionCount}>{likesCount.toLocaleString()}</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.actionButton} onPress={() => onCommentPress(item)}>
          <Feather name="message-circle" size={24} color="white" />
          <Text style={styles.actionCount}>{item.comments_count.toLocaleString()}</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.actionButton}>
          <Feather name="download" size={24} color="white" />
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.actionButton}>
          <Feather name="share" size={24} color="white" />
        </TouchableOpacity>
      </View>

      {/* Caption and Metadata */}
      <View style={styles.postInfo}>
        <Text style={styles.caption}>{item.caption}</Text>
        {item.location && (
          <View style={styles.location}>
            <Feather name="map-pin" size={14} color="#8e8e8e" />
            <Text style={styles.locationText}>{item.location}</Text>
          </View>
        )}
        <Text style={styles.postDate}>
          {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
        </Text>
      </View>
    </View>
  );
};

// Comment Section Component
const CommentSection = ({ post, onClose, commentText, setCommentText, onPostComment }) => {
  const [comments, setComments] = useState([]);
  const [loadingComments, setLoadingComments] = useState(true);

  useEffect(() => {
    // Fetch comments for the post
    const fetchComments = async () => {
      try {
        const response = await fetch(`/api/posts/${post.id}/comments/`);
        const data = await response.json();
        setComments(data);
      } catch (error) {
        console.error('Error fetching comments:', error);
      } finally {
        setLoadingComments(false);
      }
    };
    
    fetchComments();
  }, []);

  return (
    <View style={styles.commentContainer}>
      {/* Header */}
      <View style={styles.commentHeader}>
        <Text style={styles.commentTitle}>Comments</Text>
        <TouchableOpacity onPress={onClose}>
          <Ionicons name="close" size={28} color="#666" />
        </TouchableOpacity>
      </View>

      {/* Comments List */}
      <ScrollView style={styles.commentsList}>
        {loadingComments ? (
          <ActivityIndicator size="small" style={styles.commentLoader} />
        ) : comments.length === 0 ? (
          <Text style={styles.noComments}>No comments yet. Be the first to comment!</Text>
        ) : (
          comments.map(comment => (
            <CommentItem key={comment.id} comment={comment} />
          ))
        )}
      </ScrollView>

      {/* Comment Input */}
      <View style={styles.commentInputContainer}>
        <TextInput
          style={styles.commentInput}
          placeholder="Add a comment..."
          value={commentText}
          onChangeText={setCommentText}
        />
        <TouchableOpacity style={styles.postButton} onPress={onPostComment}>
          <Text style={styles.postButtonText}>Post</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

// Helper Components
const TabButton = ({ icon, label, active, onPress }) => (
  <TouchableOpacity
    style={[styles.tabButton, active && styles.activeTab]}
    onPress={onPress}
  >
    <FontAwesome 
      name={icon} 
      size={20} 
      color={active ? "#3897f0" : "#65676b"} 
    />
    <Text style={[styles.tabLabel, active && styles.activeLabel]}>{label}</Text>
  </TouchableOpacity>
);

const CommentItem = ({ comment }) => (
  <View style={styles.commentItem}>
    <Image 
      source={{ uri: comment.user.profile_picture || 'https://via.placeholder.com/40' }} 
      style={styles.commentProfilePic}
    />
    <View style={styles.commentContent}>
      <Text style={styles.commentUsername}>@{comment.user.username}</Text>
      <Text style={styles.commentText}>{comment.text}</Text>
      <View style={styles.commentActions}>
        <Text style={styles.commentTime}>
          {new Date(comment.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
        <TouchableOpacity style={styles.commentAction}>
          <FontAwesome 
            name={comment.is_liked ? "heart" : "heart-o"} 
            size={14} 
            color={comment.is_liked ? "#ff3040" : "#8e8e8e"} 
          />
          <Text style={styles.commentActionText}>{comment.likes_count || 0}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.commentAction}>
          <Text style={styles.commentActionText}>Reply</Text>
        </TouchableOpacity>
      </View>
    </View>
  </View>
);

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f2f5',
  },
  tabBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 15,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  tabButton: {
    alignItems: 'center',
    padding: 8,
    borderRadius: 8,
  },
  activeTab: {
    backgroundColor: '#f0f2f5',
  },
  tabLabel: {
    marginTop: 5,
    color: '#65676b',
    fontSize: 12,
  },
  activeLabel: {
    color: '#1a1a1a',
    fontWeight: 'bold',
  },
  loader: {
    marginTop: 50,
  },
  noPosts: {
    textAlign: 'center',
    marginTop: 30,
    color: '#666',
  },
  postContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    margin: 10,
    overflow: 'hidden',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
  },
  profilePic: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 10,
  },
  username: {
    fontWeight: '600',
    fontSize: 16,
  },
  followButton: {
    marginLeft: 'auto',
    backgroundColor: '#3897f0',
    borderRadius: 20,
    paddingVertical: 6,
    paddingHorizontal: 15,
  },
  followingButton: {
    backgroundColor: '#efefef',
  },
  followText: {
    color: 'white',
    fontWeight: '600',
  },
  followingText: {
    color: '#262626',
  },
  media: {
    width: '100%',
    aspectRatio: 4/5,
    backgroundColor: '#000',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  viewCount: {
    position: 'absolute',
    top: 15,
    left: 15,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
  },
  viewCountText: {
    color: 'white',
    fontSize: 12,
    marginLeft: 5,
  },
  actionButtons: {
    position: 'absolute',
    right: 15,
    bottom: 100,
    alignItems: 'center',
  },
  actionButton: {
    alignItems: 'center',
    marginBottom: 20,
  },
  actionCount: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 5,
    textShadowColor: 'rgba(0,0,0,0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  postInfo: {
    padding: 15,
  },
  caption: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 10,
  },
  location: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 5,
  },
  locationText: {
    color: '#8e8e8e',
    fontSize: 13,
    marginLeft: 5,
  },
  postDate: {
    color: '#8e8e8e',
    fontSize: 12,
    marginTop: 8,
  },
  commentContainer: {
    flex: 1,
    backgroundColor: '#fafafa',
  },
  commentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    backgroundColor: 'white',
  },
  commentTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  commentsList: {
    flex: 1,
    padding: 15,
  },
  commentLoader: {
    marginTop: 20,
  },
  noComments: {
    textAlign: 'center',
    color: '#8e8e8e',
    marginTop: 30,
  },
  commentItem: {
    flexDirection: 'row',
    marginBottom: 16,
    padding: 12,
    backgroundColor: 'white',
    borderRadius: 16,
    elevation: 1,
  },
  commentProfilePic: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
  },
  commentContent: {
    flex: 1,
  },
  commentUsername: {
    fontWeight: '600',
    marginBottom: 5,
  },
  commentText: {
    fontSize: 15,
    lineHeight: 20,
  },
  commentActions: {
    flexDirection: 'row',
    marginTop: 8,
    alignItems: 'center',
  },
  commentTime: {
    color: '#8e8e8e',
    fontSize: 12,
    marginRight: 15,
  },
  commentAction: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 15,
  },
  commentActionText: {
    color: '#8e8e8e',
    fontSize: 12,
    marginLeft: 5,
  },
  commentInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#eee',
    backgroundColor: 'white',
  },
  commentInput: {
    flex: 1,
    backgroundColor: '#f0f2f5',
    borderRadius: 24,
    paddingVertical: 12,
    paddingHorizontal: 16,
    paddingRight: 50,
    fontSize: 15,
  },
  postButton: {
    position: 'absolute',
    right: 25,
    backgroundColor: '#3897f0',
    borderRadius: 24,
    paddingVertical: 8,
    paddingHorizontal: 20,
  },
  postButtonText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 15,
  },
});

export default FeedScreen;