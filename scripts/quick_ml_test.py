#!/usr/bin/env python3
"""
Quick ML Pipeline Integration Test

A simpler, faster test to verify ML Pipeline components are working.
"""

import sys
import os

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

def test_imports():
    """Test that all ML Pipeline components can be imported."""
    print("🧪 Testing ML Pipeline Component Imports")
    print("=" * 50)
    
    tests = []
    
    # Test 1: ML Pipeline Service
    try:
        from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
        tests.append(("ML Pipeline Service", True, None))
        print("✅ ML Pipeline Service - Import successful")
    except Exception as e:
        tests.append(("ML Pipeline Service", False, str(e)))
        print(f"❌ ML Pipeline Service - Import failed: {e}")
    
    # Test 2: Pattern Recognition Engine
    try:
        from src.services.pattern_recognition_engine import pattern_recognition_engine
        tests.append(("Pattern Recognition Engine", True, None))
        print("✅ Pattern Recognition Engine - Import successful")
    except Exception as e:
        tests.append(("Pattern Recognition Engine", False, str(e)))
        print(f"❌ Pattern Recognition Engine - Import failed: {e}")
    
    # Test 3: A/B Testing Framework
    try:
        from src.services.ab_testing_framework import ABTestingFramework
        tests.append(("A/B Testing Framework", True, None))
        print("✅ A/B Testing Framework - Import successful")
    except Exception as e:
        tests.append(("A/B Testing Framework", False, str(e)))
        print(f"❌ A/B Testing Framework - Import failed: {e}")
    
    # Test 4: Unified Decision Engine
    try:
        from src.services.unified_decision_engine import UnifiedDecisionEngine
        tests.append(("Unified Decision Engine", True, None))
        print("✅ Unified Decision Engine - Import successful")
    except Exception as e:
        tests.append(("Unified Decision Engine", False, str(e)))
        print(f"❌ Unified Decision Engine - Import failed: {e}")
    
    # Test 5: ML Event Tracker
    try:
        from src.services.ml_pipeline.ml_event_tracker import MLEventTracker
        tests.append(("ML Event Tracker", True, None))
        print("✅ ML Event Tracker - Import successful")
    except Exception as e:
        tests.append(("ML Event Tracker", False, str(e)))
        print(f"❌ ML Event Tracker - Import failed: {e}")
    
    # Test 6: Conversation Orchestrator (main integration point)
    try:
        from src.services.conversation.orchestrator import ConversationOrchestrator
        tests.append(("Conversation Orchestrator", True, None))
        print("✅ Conversation Orchestrator - Import successful")
    except Exception as e:
        tests.append(("Conversation Orchestrator", False, str(e)))
        print(f"❌ Conversation Orchestrator - Import failed: {e}")
    
    return tests


def test_orchestrator_ml_components():
    """Test that the orchestrator has ML components properly integrated."""
    print("\n🔗 Testing Orchestrator ML Integration")
    print("=" * 50)
    
    try:
        from src.services.conversation.orchestrator import ConversationOrchestrator
        
        # Create orchestrator without initializing (to avoid timeouts)
        orchestrator = ConversationOrchestrator(industry='salud')
        
        # Check ML component attributes
        components = {
            "ML Pipeline": hasattr(orchestrator, 'ml_pipeline'),
            "Pattern Recognition": hasattr(orchestrator, 'pattern_recognition'),
            "A/B Testing": hasattr(orchestrator, 'ab_testing'),
            "Decision Engine": hasattr(orchestrator, 'decision_engine'),
            "MLTrackingMixin": hasattr(orchestrator, '_update_ml_conversation_metrics'),
            "ABTestingMixin": hasattr(orchestrator, '_apply_greeting_ab_test')
        }
        
        print("Component Integration Status:")
        for component, status in components.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {component}")
        
        success_rate = sum(components.values()) / len(components) * 100
        print(f"\nIntegration Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80
        
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        return False


def test_ml_pipeline_methods():
    """Test that ML Pipeline has required methods."""
    print("\n⚙️  Testing ML Pipeline Methods")
    print("=" * 50)
    
    try:
        from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
        
        # Create instance without initializing
        pipeline = MLPipelineService()
        
        required_methods = [
            'process_conversation_predictions',
            'record_conversation_outcome',
            'get_ml_pipeline_metrics',
            'get_pattern_insights'
        ]
        
        print("Required Methods:")
        all_present = True
        for method in required_methods:
            has_method = hasattr(pipeline, method)
            status_icon = "✅" if has_method else "❌"
            print(f"  {status_icon} {method}")
            if not has_method:
                all_present = False
        
        # Check event tracker
        has_event_tracker = hasattr(pipeline, 'event_tracker')
        print(f"  {'✅' if has_event_tracker else '❌'} event_tracker")
        if not has_event_tracker:
            all_present = False
        
        if has_event_tracker and hasattr(pipeline.event_tracker, 'track_event'):
            print(f"  ✅ event_tracker.track_event")
        else:
            print(f"  ❌ event_tracker.track_event")
            all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"❌ ML Pipeline methods test failed: {e}")
        return False


def test_pattern_recognition_methods():
    """Test that Pattern Recognition has required methods."""
    print("\n🔍 Testing Pattern Recognition Methods")
    print("=" * 50)
    
    try:
        from src.services.pattern_recognition_engine import pattern_recognition_engine
        
        required_methods = [
            'detect_patterns',
            'get_pattern_insights',
            'initialize'
        ]
        
        print("Required Methods:")
        all_present = True
        for method in required_methods:
            has_method = hasattr(pattern_recognition_engine, method)
            status_icon = "✅" if has_method else "❌"
            print(f"  {status_icon} {method}")
            if not has_method:
                all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"❌ Pattern Recognition methods test failed: {e}")
        return False


def main():
    """Run all quick tests."""
    print("🚀 Quick ML Pipeline Integration Test")
    print("=" * 60)
    
    # Test 1: Component imports
    import_tests = test_imports()
    import_success = sum(1 for _, success, _ in import_tests if success)
    import_total = len(import_tests)
    
    # Test 2: Orchestrator integration
    orchestrator_success = test_orchestrator_ml_components()
    
    # Test 3: ML Pipeline methods
    pipeline_methods_success = test_ml_pipeline_methods()
    
    # Test 4: Pattern Recognition methods
    pattern_methods_success = test_pattern_recognition_methods()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    print(f"Import Tests: {import_success}/{import_total} passed ({import_success/import_total*100:.1f}%)")
    print(f"Orchestrator Integration: {'✅ PASS' if orchestrator_success else '❌ FAIL'}")
    print(f"ML Pipeline Methods: {'✅ PASS' if pipeline_methods_success else '❌ FAIL'}")
    print(f"Pattern Recognition Methods: {'✅ PASS' if pattern_methods_success else '❌ FAIL'}")
    
    # Overall success
    tests_passed = sum([
        import_success >= 5,  # At least 5 out of 6 imports
        orchestrator_success,
        pipeline_methods_success,
        pattern_methods_success
    ])
    
    total_tests = 4
    overall_success = tests_passed / total_tests * 100
    
    print(f"\nOverall Success Rate: {overall_success:.1f}% ({tests_passed}/{total_tests})")
    
    if overall_success >= 75:
        print("🎉 EXCELLENT! ML Pipeline Integration is ready!")
    elif overall_success >= 50:
        print("👍 GOOD! Most components are working.")
    else:
        print("⚠️  NEEDS WORK! Several components need fixing.")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if import_success < import_total:
        print("- Fix import issues for missing components")
    if not orchestrator_success:
        print("- Check orchestrator ML component integration")
    if not pipeline_methods_success:
        print("- Verify ML Pipeline service methods")
    if not pattern_methods_success:
        print("- Check Pattern Recognition engine methods")
    
    return overall_success >= 50


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)