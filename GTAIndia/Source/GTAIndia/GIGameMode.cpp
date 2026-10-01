#include "GIGameMode.h"
#include "GIHUD.h"
#include "GIPlayerCharacter.h"
#include "GIPlayerController.h"

AGIGameMode::AGIGameMode()
{
	DefaultPawnClass = AGIPlayerCharacter::StaticClass();
	PlayerControllerClass = AGIPlayerController::StaticClass();
	HUDClass = AGIHUD::StaticClass();
}
