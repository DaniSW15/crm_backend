class DomainException(Exception):
    """Excepción base para violaciones de reglas de negocio en la capa de dominio."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EntityNotFoundException(DomainException):
    """Entidad no encontrada en el repositorio."""
    pass


class BusinessRuleViolationException(DomainException):
    """Operación inválida según las reglas de negocio."""
    pass

