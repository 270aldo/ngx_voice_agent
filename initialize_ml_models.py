#!/usr/bin/env python3
"""
Initialize ML Models for NGX Voice Sales Agent.

Run this script to train the ML models with synthetic data and prepare them for use.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.services.training.training_data_generator import TrainingDataGenerator
from src.services.training.ml_model_trainer import MLModelTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Train and initialize all ML models."""
    print("\n🚀 NGX ML Model Initialization")
    print("=" * 50)
    print("This will train ML models for:")
    print("  • Objection Prediction")
    print("  • Needs Analysis") 
    print("  • Conversion Prediction")
    print("=" * 50)
    
    try:
        # Step 1: Generate training data
        print("\n📊 Generating synthetic training data...")
        generator = TrainingDataGenerator()
        dataset = generator.generate_complete_training_dataset()
        
        print(f"✓ Generated {sum(len(data) for data in dataset.values())} total training samples")
        
        # Step 2: Initialize trainer
        print("\n🤖 Initializing ML trainer...")
        trainer = MLModelTrainer(models_dir="models")
        
        # Step 3: Train models
        print("\n🎯 Training models...")
        
        # Objection model
        print("\n1. Training Objection Prediction Model")
        print("-" * 40)
        obj_result = trainer.train_objection_model(dataset["objection"])
        if obj_result["success"]:
            print(f"✓ Model: {obj_result['model_type']}")
            print(f"✓ Accuracy: {obj_result['accuracy']:.1%}")
            print(f"✓ Saved to: {obj_result['model_path']}")
        else:
            print("✗ Failed to train objection model")
        
        # Needs model
        print("\n2. Training Needs Analysis Model")
        print("-" * 40)
        needs_result = trainer.train_needs_model(dataset["needs"])
        if needs_result["success"]:
            print(f"✓ Model: {needs_result['model_type']}")
            print(f"✓ Accuracy: {needs_result['accuracy']:.1%}")
            print(f"✓ Saved to: {needs_result['model_path']}")
        else:
            print("✗ Failed to train needs model")
        
        # Conversion model
        print("\n3. Training Conversion Prediction Model")
        print("-" * 40)
        conv_result = trainer.train_conversion_model(dataset["conversion"])
        if conv_result["success"]:
            print(f"✓ Model: {conv_result['model_type']}")
            print(f"✓ Accuracy: {conv_result['accuracy']:.1%}")
            print(f"✓ Saved to: {conv_result['model_path']}")
        else:
            print("✗ Failed to train conversion model")
        
        # Summary
        print("\n" + "=" * 50)
        print("✅ ML MODEL INITIALIZATION COMPLETE!")
        print("=" * 50)
        print("\nModels are now ready for use in:")
        print("  • ObjectionPredictionService")
        print("  • NeedsPredictionService")
        print("  • ConversionPredictionService")
        print("\nTo use ML predictions, the services will automatically")
        print("load these models when initialized.")
        
        # Optional: Export training data for reference
        print("\n💾 Saving training data for reference...")
        generator.export_training_data(dataset, "training_data_reference.json")
        print("✓ Training data saved to: training_data_reference.json")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Model initialization failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    print("\n🏋️ NGX Voice Sales Agent - ML Model Trainer")
    print("Specialized for Fitness & Wellness Industry")
    
    # Run the async main function
    asyncio.run(main())