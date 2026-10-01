#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "GIInput.generated.h"

class UInputAction;
class UInputMappingContext;

/**
 * Enhanced Input actions and mapping contexts, built in code at startup (no editor assets).
 * Keyboard + mouse and gamepad are both mapped.
 */
UCLASS()
class GTAINDIA_API UGIInput : public UObject
{
	GENERATED_BODY()

public:
	static UGIInput& Get();

	// On foot
	UPROPERTY() TObjectPtr<UInputAction> Move;
	UPROPERTY() TObjectPtr<UInputAction> Look;
	UPROPERTY() TObjectPtr<UInputAction> Jump;
	UPROPERTY() TObjectPtr<UInputAction> Sprint;
	UPROPERTY() TObjectPtr<UInputAction> Interact;
	UPROPERTY() TObjectPtr<UInputAction> Vehicle;
	UPROPERTY() TObjectPtr<UInputAction> Pause;
	UPROPERTY() TObjectPtr<UInputAction> Dive;
	UPROPERTY() TObjectPtr<UInputAction> Walk;
	// Vehicle
	UPROPERTY() TObjectPtr<UInputAction> Throttle;
	UPROPERTY() TObjectPtr<UInputAction> Steer;
	UPROPERTY() TObjectPtr<UInputAction> Brake;
	UPROPERTY() TObjectPtr<UInputAction> Horn;

	UPROPERTY() TObjectPtr<UInputMappingContext> OnFoot;
	UPROPERTY() TObjectPtr<UInputMappingContext> Driving;
	/** Always active: pause + look. */
	UPROPERTY() TObjectPtr<UInputMappingContext> Common;

private:
	void Build();
};
