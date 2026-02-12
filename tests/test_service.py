from app.services.example_service import ExampleService

def test_example_service():
    service = ExampleService()
    assert service.get_message() == "Hello from service"
