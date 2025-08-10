"""
ML Model Trainer for NGX Voice Sales Agent.

This module implements the actual machine learning models using scikit-learn
for objection prediction, needs analysis, and conversion probability.
"""

import json
import logging
import pickle
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import joblib

logger = logging.getLogger(__name__)

class MLModelTrainer:
    """
    Trains and manages machine learning models for predictive services.
    """
    
    def __init__(self, models_dir: str = "models"):
        """
        Initialize the ML model trainer.
        
        Args:
            models_dir: Directory to save trained models
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.models = {}
        self.vectorizers = {}
        self.scalers = {}
        
    def train_objection_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train model for objection prediction.
        
        Args:
            training_data: List of training samples with features and labels
            
        Returns:
            Training results including accuracy and model info
        """
        logger.info("Training objection prediction model...")
        
        # Extract features and labels
        X_text = []
        X_numeric = []
        y = []
        
        for sample in training_data:
            features = sample["features"]
            label = sample["label"]
            
            # Text features: last message
            X_text.append(features.get("last_message", ""))
            
            # Numeric features
            numeric_features = [
                features.get("message_count", 0),
                1 if features.get("contains_price_mention", False) else 0,
                1 if features.get("contains_comparison", False) else 0,
                1 if features.get("sentiment_trend") == "negative" else 0,
                features.get("objection_keywords", 0)
            ]
            X_numeric.append(numeric_features)
            
            y.append(label)
        
        # Convert to numpy arrays
        X_numeric = np.array(X_numeric)
        
        # Create text vectorizer
        text_vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words=None,  # Keep Spanish stop words for now
            min_df=2
        )
        
        # Transform text features
        X_text_vectorized = text_vectorizer.fit_transform(X_text)
        
        # Combine features
        X_combined = np.hstack([X_text_vectorized.toarray(), X_numeric])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train multiple models and select best
        models = {
            "random_forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight="balanced"
            ),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            ),
            "logistic_regression": LogisticRegression(
                C=1.0,
                random_state=42,
                max_iter=1000,
                class_weight="balanced"
            )
        }
        
        best_model = None
        best_score = 0
        best_model_name = None
        
        for model_name, model in models.items():
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"{model_name} accuracy: {accuracy:.3f}")
            
            if accuracy > best_score:
                best_score = accuracy
                best_model = model
                best_model_name = model_name
        
        # Calculate detailed metrics for best model
        y_pred = best_model.predict(X_test)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average='weighted'
        )
        
        # Save the best model and vectorizer
        model_info = {
            "model": best_model,
            "vectorizer": text_vectorizer,
            "feature_names": ["message_count", "contains_price_mention", 
                             "contains_comparison", "sentiment_negative", "objection_keywords"],
            "model_type": best_model_name,
            "trained_at": datetime.now().isoformat()
        }
        
        model_path = self.models_dir / "objection_model.pkl"
        joblib.dump(model_info, model_path)
        
        self.models["objection"] = model_info
        
        return {
            "success": True,
            "model_type": best_model_name,
            "accuracy": best_score,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "model_path": str(model_path)
        }
    
    def train_needs_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train model for needs prediction.
        
        Args:
            training_data: List of training samples with features and labels
            
        Returns:
            Training results including accuracy and model info
        """
        logger.info("Training needs prediction model...")
        
        # Extract features and labels
        X_text = []
        X_numeric = []
        y = []
        
        for sample in training_data:
            features = sample["features"]
            label = sample["label"]
            
            # Combine all messages for text analysis
            messages_text = " ".join([msg["content"] for msg in features.get("messages", [])])
            X_text.append(messages_text)
            
            # Numeric features
            numeric_features = [
                features.get("question_count", 0),
                1 if features.get("mentions_specific_feature", False) else 0,
                features.get("engagement_level", 0)
            ]
            X_numeric.append(numeric_features)
            
            y.append(label)
        
        # Convert to numpy arrays
        X_numeric = np.array(X_numeric)
        
        # Create text vectorizer
        text_vectorizer = TfidfVectorizer(
            max_features=150,
            ngram_range=(1, 3),
            min_df=1
        )
        
        # Transform text features
        X_text_vectorized = text_vectorizer.fit_transform(X_text)
        
        # Scale numeric features
        scaler = StandardScaler()
        X_numeric_scaled = scaler.fit_transform(X_numeric)
        
        # Combine features
        X_combined = np.hstack([X_text_vectorized.toarray(), X_numeric_scaled])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train SVM model (good for text classification)
        model = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            probability=True,
            random_state=42,
            class_weight='balanced'
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average='weighted'
        )
        
        # Save model
        model_info = {
            "model": model,
            "vectorizer": text_vectorizer,
            "scaler": scaler,
            "feature_names": ["question_count", "mentions_specific_feature", "engagement_level"],
            "model_type": "svm",
            "trained_at": datetime.now().isoformat()
        }
        
        model_path = self.models_dir / "needs_model.pkl"
        joblib.dump(model_info, model_path)
        
        self.models["needs"] = model_info
        
        return {
            "success": True,
            "model_type": "svm",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "model_path": str(model_path)
        }
    
    def train_conversion_model(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train model for conversion probability prediction.
        
        Args:
            training_data: List of training samples with features and labels
            
        Returns:
            Training results including accuracy and model info
        """
        logger.info("Training conversion prediction model...")
        
        # Extract features and labels
        X_text = []
        X_numeric = []
        y_binary = []  # For classification (will convert/won't convert)
        y_probability = []  # For regression (probability value)
        
        for sample in training_data:
            features = sample["features"]
            label = sample["label"]
            
            # Combine all messages for text analysis
            messages_text = " ".join([msg["content"] for msg in features.get("messages", [])])
            X_text.append(messages_text)
            
            # Numeric features
            numeric_features = [
                features.get("positive_signals", 0),
                features.get("questions_asked", 0),
                features.get("message_length_avg", 0),
                features.get("engagement_score", 0)
            ]
            X_numeric.append(numeric_features)
            
            # Labels
            y_binary.append(1 if label["did_convert"] else 0)
            y_probability.append(label["probability"])
        
        # Convert to numpy arrays
        X_numeric = np.array(X_numeric)
        y_binary = np.array(y_binary)
        
        # Create text vectorizer
        text_vectorizer = TfidfVectorizer(
            max_features=200,
            ngram_range=(1, 3),
            min_df=1
        )
        
        # Transform text features
        X_text_vectorized = text_vectorizer.fit_transform(X_text)
        
        # Scale numeric features
        scaler = StandardScaler()
        X_numeric_scaled = scaler.fit_transform(X_numeric)
        
        # Combine features
        X_combined = np.hstack([X_text_vectorized.toarray(), X_numeric_scaled])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y_binary, test_size=0.2, random_state=42, stratify=y_binary
        )
        
        # Train Gradient Boosting model (good for probability estimation)
        model = GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=6,
            min_samples_split=20,
            min_samples_leaf=10,
            subsample=0.8,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average='weighted'
        )
        
        # Save model
        model_info = {
            "model": model,
            "vectorizer": text_vectorizer,
            "scaler": scaler,
            "feature_names": ["positive_signals", "questions_asked", 
                             "message_length_avg", "engagement_score"],
            "model_type": "gradient_boosting",
            "trained_at": datetime.now().isoformat()
        }
        
        model_path = self.models_dir / "conversion_model.pkl"
        joblib.dump(model_info, model_path)
        
        self.models["conversion"] = model_info
        
        return {
            "success": True,
            "model_type": "gradient_boosting",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "model_path": str(model_path)
        }
    
    def load_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a trained model from disk.
        
        Args:
            model_name: Name of the model to load (objection, needs, conversion)
            
        Returns:
            Model info dictionary or None if not found
        """
        try:
            model_path = self.models_dir / f"{model_name}_model.pkl"
            if model_path.exists():
                model_info = joblib.load(model_path)
                self.models[model_name] = model_info
                logger.info(f"Loaded {model_name} model from {model_path}")
                return model_info
            else:
                logger.warning(f"Model file not found: {model_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return None
    
    def predict_objection(self, messages: List[Dict[str, Any]], 
                         threshold: float = 0.5) -> Dict[str, Any]:
        """
        Predict objection type from conversation.
        
        Args:
            messages: Conversation messages
            threshold: Confidence threshold for predictions
            
        Returns:
            Prediction results with objection types and confidence
        """
        if "objection" not in self.models:
            self.load_model("objection")
            
        if "objection" not in self.models:
            return {"error": "Objection model not loaded"}
        
        model_info = self.models["objection"]
        model = model_info["model"]
        vectorizer = model_info["vectorizer"]
        
        # Extract features
        last_message = messages[-1]["content"] if messages else ""
        
        # Numeric features
        numeric_features = [
            len(messages),
            1 if any("precio" in msg["content"].lower() or "$" in msg["content"] for msg in messages) else 0,
            1 if any("otro" in msg["content"].lower() or "competencia" in msg["content"].lower() for msg in messages) else 0,
            1,  # Assume negative sentiment for now
            0   # Objection keywords count
        ]
        
        # Vectorize text
        X_text = vectorizer.transform([last_message])
        
        # Combine features
        X_combined = np.hstack([X_text.toarray(), np.array([numeric_features])])
        
        # Predict
        prediction = model.predict(X_combined)[0]
        probabilities = model.predict_proba(X_combined)[0]
        
        # Get confidence
        confidence = max(probabilities)
        
        # Get top predictions
        classes = model.classes_
        predictions = []
        
        for i, (cls, prob) in enumerate(zip(classes, probabilities)):
            if prob >= threshold:
                predictions.append({
                    "type": cls,
                    "confidence": float(prob)
                })
        
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "primary_objection": prediction,
            "confidence": float(confidence),
            "all_predictions": predictions[:3]  # Top 3 predictions
        }
    
    def predict_needs(self, messages: List[Dict[str, Any]], 
                     threshold: float = 0.4) -> Dict[str, Any]:
        """
        Predict customer needs from conversation.
        
        Args:
            messages: Conversation messages
            threshold: Confidence threshold for predictions
            
        Returns:
            Prediction results with need categories and confidence
        """
        if "needs" not in self.models:
            self.load_model("needs")
            
        if "needs" not in self.models:
            return {"error": "Needs model not loaded"}
        
        model_info = self.models["needs"]
        model = model_info["model"]
        vectorizer = model_info["vectorizer"]
        scaler = model_info["scaler"]
        
        # Extract features
        messages_text = " ".join([msg["content"] for msg in messages])
        
        # Numeric features
        question_count = sum(1 for msg in messages if "?" in msg["content"])
        mentions_feature = 1 if any(word in messages_text.lower() for word in ["función", "característica", "incluye"]) else 0
        engagement_level = len(messages) / 10.0
        
        numeric_features = [[question_count, mentions_feature, engagement_level]]
        
        # Transform features
        X_text = vectorizer.transform([messages_text])
        X_numeric = scaler.transform(numeric_features)
        
        # Combine features
        X_combined = np.hstack([X_text.toarray(), X_numeric])
        
        # Predict
        prediction = model.predict(X_combined)[0]
        probabilities = model.predict_proba(X_combined)[0]
        
        # Get confidence
        confidence = max(probabilities)
        
        # Get all predictions above threshold
        classes = model.classes_
        predictions = []
        
        for cls, prob in zip(classes, probabilities):
            if prob >= threshold:
                predictions.append({
                    "need": cls,
                    "confidence": float(prob)
                })
        
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "primary_need": prediction,
            "confidence": float(confidence),
            "all_needs": predictions
        }
    
    def predict_conversion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict conversion probability from conversation.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Prediction results with conversion probability and signals
        """
        if "conversion" not in self.models:
            self.load_model("conversion")
            
        if "conversion" not in self.models:
            return {"error": "Conversion model not loaded"}
        
        model_info = self.models["conversion"]
        model = model_info["model"]
        vectorizer = model_info["vectorizer"]
        scaler = model_info["scaler"]
        
        # Extract features
        messages_text = " ".join([msg["content"] for msg in messages])
        
        # Count positive signals
        positive_signals = sum(1 for msg in messages if any(
            signal in msg["content"].lower() for signal in ["interesa", "gusta", "quiero", "perfecto", "excelente"]
        ))
        
        # Numeric features
        questions_asked = sum(1 for msg in messages if msg["role"] == "user" and "?" in msg["content"])
        message_length_avg = sum(len(msg["content"]) for msg in messages) / len(messages) if messages else 0
        engagement_score = len(messages) * 0.1 + (positive_signals * 0.2)
        
        numeric_features = [[positive_signals, questions_asked, message_length_avg, engagement_score]]
        
        # Transform features
        X_text = vectorizer.transform([messages_text])
        X_numeric = scaler.transform(numeric_features)
        
        # Combine features
        X_combined = np.hstack([X_text.toarray(), X_numeric])
        
        # Predict
        prediction = model.predict(X_combined)[0]
        probability = model.predict_proba(X_combined)[0, 1]
        
        # Determine conversion level
        if probability >= 0.7:
            level = "high"
        elif probability >= 0.4:
            level = "medium"
        else:
            level = "low"
        
        return {
            "will_convert": bool(prediction),
            "probability": float(probability),
            "conversion_level": level,
            "positive_signals": positive_signals,
            "engagement_score": float(engagement_score)
        }