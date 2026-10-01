#include "GIInput.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "InputCoreTypes.h"
#include "UObject/Package.h"

namespace
{
	UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(Outer, FName(Name));
		A->ValueType = Type;
		return A;
	}

	UInputModifierNegate* Negate(UObject* Outer, bool X, bool Y, bool Z)
	{
		UInputModifierNegate* M = NewObject<UInputModifierNegate>(Outer);
		M->bX = X;
		M->bY = Y;
		M->bZ = Z;
		return M;
	}

	UInputModifierSwizzleAxis* SwizzleYXZ(UObject* Outer)
	{
		UInputModifierSwizzleAxis* M = NewObject<UInputModifierSwizzleAxis>(Outer);
		M->Order = EInputAxisSwizzle::YXZ;
		return M;
	}

	UInputModifierDeadZone* DeadZone(UObject* Outer, float Lower = 0.18f)
	{
		UInputModifierDeadZone* M = NewObject<UInputModifierDeadZone>(Outer);
		M->LowerThreshold = Lower;
		M->Type = EDeadZoneType::Radial;
		return M;
	}

	void Map(UInputMappingContext* Ctx, UInputAction* Action, const FKey& Key, std::initializer_list<UInputModifier*> Mods = {})
	{
		FEnhancedActionKeyMapping& M = Ctx->MapKey(Action, Key);
		for (UInputModifier* Mod : Mods)
		{
			M.Modifiers.Add(Mod);
		}
	}
}

UGIInput& UGIInput::Get()
{
	static UGIInput* Instance = nullptr;
	if (!Instance)
	{
		Instance = NewObject<UGIInput>(GetTransientPackage(), TEXT("GIInput"));
		Instance->AddToRoot();
		Instance->Build();
	}
	return *Instance;
}

void UGIInput::Build()
{
	Move = MakeAction(this, TEXT("IA_Move"), EInputActionValueType::Axis2D);
	Look = MakeAction(this, TEXT("IA_Look"), EInputActionValueType::Axis2D);
	Jump = MakeAction(this, TEXT("IA_Jump"), EInputActionValueType::Boolean);
	Sprint = MakeAction(this, TEXT("IA_Sprint"), EInputActionValueType::Boolean);
	Interact = MakeAction(this, TEXT("IA_Interact"), EInputActionValueType::Boolean);
	Vehicle = MakeAction(this, TEXT("IA_Vehicle"), EInputActionValueType::Boolean);
	Pause = MakeAction(this, TEXT("IA_Pause"), EInputActionValueType::Boolean);
	Dive = MakeAction(this, TEXT("IA_Dive"), EInputActionValueType::Boolean);
	Walk = MakeAction(this, TEXT("IA_Walk"), EInputActionValueType::Boolean);
	Throttle = MakeAction(this, TEXT("IA_Throttle"), EInputActionValueType::Axis1D);
	Steer = MakeAction(this, TEXT("IA_Steer"), EInputActionValueType::Axis1D);
	Brake = MakeAction(this, TEXT("IA_Brake"), EInputActionValueType::Boolean);
	Horn = MakeAction(this, TEXT("IA_Horn"), EInputActionValueType::Boolean);

	Common = NewObject<UInputMappingContext>(this, TEXT("IMC_Common"));
	Map(Common, Look, EKeys::Mouse2D, { Negate(this, false, true, false) });
	Map(Common, Look, EKeys::Gamepad_Right2D, { DeadZone(this), Negate(this, false, true, false) });
	Map(Common, Pause, EKeys::Escape);
	Map(Common, Pause, EKeys::P);
	Map(Common, Pause, EKeys::Gamepad_Special_Right);
	Map(Common, Vehicle, EKeys::F);
	Map(Common, Vehicle, EKeys::Gamepad_FaceButton_Top);

	OnFoot = NewObject<UInputMappingContext>(this, TEXT("IMC_OnFoot"));
	Map(OnFoot, Move, EKeys::W, { SwizzleYXZ(this) });
	Map(OnFoot, Move, EKeys::Up, { SwizzleYXZ(this) });
	Map(OnFoot, Move, EKeys::S, { SwizzleYXZ(this), Negate(this, true, true, true) });
	Map(OnFoot, Move, EKeys::Down, { SwizzleYXZ(this), Negate(this, true, true, true) });
	Map(OnFoot, Move, EKeys::A, { Negate(this, true, true, true) });
	Map(OnFoot, Move, EKeys::Left, { Negate(this, true, true, true) });
	Map(OnFoot, Move, EKeys::D);
	Map(OnFoot, Move, EKeys::Right);
	Map(OnFoot, Move, EKeys::Gamepad_Left2D, { DeadZone(this) });
	Map(OnFoot, Jump, EKeys::SpaceBar);
	Map(OnFoot, Jump, EKeys::Gamepad_FaceButton_Bottom);
	Map(OnFoot, Sprint, EKeys::LeftShift);
	Map(OnFoot, Sprint, EKeys::Gamepad_LeftThumbstick);
	Map(OnFoot, Sprint, EKeys::Gamepad_RightTrigger);
	Map(OnFoot, Walk, EKeys::LeftAlt);
	Map(OnFoot, Dive, EKeys::C);
	Map(OnFoot, Dive, EKeys::LeftControl);
	Map(OnFoot, Dive, EKeys::Gamepad_FaceButton_Right);
	Map(OnFoot, Interact, EKeys::E);
	Map(OnFoot, Interact, EKeys::Gamepad_FaceButton_Left);

	Driving = NewObject<UInputMappingContext>(this, TEXT("IMC_Driving"));
	Map(Driving, Throttle, EKeys::W);
	Map(Driving, Throttle, EKeys::Up);
	Map(Driving, Throttle, EKeys::S, { Negate(this, true, true, true) });
	Map(Driving, Throttle, EKeys::Down, { Negate(this, true, true, true) });
	Map(Driving, Throttle, EKeys::Gamepad_RightTriggerAxis);
	Map(Driving, Throttle, EKeys::Gamepad_LeftTriggerAxis, { Negate(this, true, true, true) });
	Map(Driving, Steer, EKeys::D);
	Map(Driving, Steer, EKeys::Right);
	Map(Driving, Steer, EKeys::A, { Negate(this, true, true, true) });
	Map(Driving, Steer, EKeys::Left, { Negate(this, true, true, true) });
	Map(Driving, Steer, EKeys::Gamepad_LeftX, { DeadZone(this, 0.12f) });
	Map(Driving, Brake, EKeys::SpaceBar);
	Map(Driving, Brake, EKeys::Gamepad_FaceButton_Bottom);
	Map(Driving, Horn, EKeys::H);
	Map(Driving, Horn, EKeys::Gamepad_LeftShoulder);
	Map(Driving, Interact, EKeys::E);
	Map(Driving, Interact, EKeys::Gamepad_FaceButton_Left);
}
